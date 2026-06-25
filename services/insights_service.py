"""
Health Insights Engine
Uses scikit-learn for:
  - Anomaly detection (IsolationForest) on vitals
  - Trend analysis (linear regression) for mood/energy/sleep
  - Symptom co-occurrence pattern mining
"""
import numpy as np
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from loguru import logger

from models.schemas import (
    HealthInsightsRequest, HealthInsightsResponse, InsightItem
)


def _parse_dates(logs: list) -> List[datetime]:
    dates = []
    for log in logs:
        try:
            dates.append(datetime.fromisoformat(log.date.replace("Z", "+00:00")))
        except Exception:
            dates.append(datetime.now())
    return dates


def _linear_trend(values: List[float]) -> str:
    """Return 'improving', 'declining', or 'stable' based on linear regression slope."""
    if len(values) < 3:
        return "stable"
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    # Simple least-squares slope
    slope = np.polyfit(x, y, 1)[0]
    if slope > 0.1:
        return "improving"
    if slope < -0.1:
        return "declining"
    return "stable"


def _detect_anomalies(values: List[float], threshold: float = 2.0) -> List[int]:
    """
    Z-score based anomaly detection (lightweight alternative to IsolationForest
    when n_samples < 10 — IsolationForest needs ≥ 10 samples).
    Returns indices of anomalous values.
    """
    if len(values) < 4:
        return []
    arr = np.array(values)
    mean, std = arr.mean(), arr.std()
    if std == 0:
        return []
    z_scores = np.abs((arr - mean) / std)
    return list(np.where(z_scores > threshold)[0])


def _detect_anomalies_isolation(values: List[float]) -> List[int]:
    """
    IsolationForest anomaly detection for larger datasets (n >= 10).
    """
    if len(values) < 10:
        return _detect_anomalies(values)
    try:
        from sklearn.ensemble import IsolationForest
        arr = np.array(values).reshape(-1, 1)
        iso = IsolationForest(contamination=0.1, random_state=42)
        preds = iso.fit_predict(arr)
        return list(np.where(preds == -1)[0])
    except Exception as e:
        logger.warning(f"IsolationForest failed: {e}")
        return _detect_anomalies(values)


def _symptom_patterns(health_logs) -> Tuple[List[str], List[str]]:
    """
    Analyse symptom co-occurrence and frequency.
    Returns (patterns: List[str], top_symptoms: List[str])
    """
    symptom_counts = Counter()
    cooccurrence = defaultdict(int)

    for log in health_logs:
        symptoms_in_log = [s.name.lower() for s in log.symptoms]
        for s in symptoms_in_log:
            symptom_counts[s] += 1
        for i, s1 in enumerate(symptoms_in_log):
            for s2 in symptoms_in_log[i+1:]:
                key = tuple(sorted([s1, s2]))
                cooccurrence[key] += 1

    patterns = []
    top_symptoms = [s for s, c in symptom_counts.most_common(5)]

    for sym, count in symptom_counts.most_common(3):
        if count >= 3:
            patterns.append(f"'{sym.title()}' appeared {count} times in the last {len(health_logs)} entries.")

    for (s1, s2), count in sorted(cooccurrence.items(), key=lambda x: -x[1])[:2]:
        if count >= 2:
            patterns.append(f"'{s1.title()}' and '{s2.title()}' frequently occur together ({count} times).")

    return patterns, top_symptoms


def _sleep_mood_correlation(health_logs) -> str:
    """Compute Pearson correlation between sleep and mood."""
    if len(health_logs) < 5:
        return None
    sleep = [l.sleepHours for l in health_logs if l.sleepHours is not None]
    mood = [l.mood for l in health_logs if l.mood is not None]
    n = min(len(sleep), len(mood))
    if n < 5:
        return None
    corr = float(np.corrcoef(sleep[:n], mood[:n])[0, 1])
    if corr > 0.5:
        return "Strong positive correlation detected between sleep duration and mood. Prioritising sleep quality is likely to improve daily mood."
    if corr < -0.3:
        return "Longer sleep is unexpectedly associated with lower mood — consider whether sleep quality (not just duration) needs addressing."
    return None


def _exercise_energy_correlation(exercise_logs, health_logs) -> str:
    """Check if exercise days correlate with higher next-day energy."""
    if len(exercise_logs) < 3 or len(health_logs) < 3:
        return None
    exercise_dates = set()
    for ex in exercise_logs:
        try:
            dt = datetime.fromisoformat(ex.date.replace("Z", "+00:00")).date()
            exercise_dates.add(dt)
        except Exception:
            pass

    energy_on_exercise = []
    energy_off_exercise = []
    for log in health_logs:
        try:
            dt = datetime.fromisoformat(log.date.replace("Z", "+00:00")).date()
            if log.energyLevel:
                if dt in exercise_dates:
                    energy_on_exercise.append(log.energyLevel)
                else:
                    energy_off_exercise.append(log.energyLevel)
        except Exception:
            pass

    if energy_on_exercise and energy_off_exercise:
        avg_ex = np.mean(energy_on_exercise)
        avg_no = np.mean(energy_off_exercise)
        if avg_ex > avg_no + 1:
            return f"Energy levels are notably higher on exercise days (avg {avg_ex:.1f} vs {avg_no:.1f}). Regular activity is positively impacting vitality."
    return None


def _compute_wellness_score(health_logs) -> float:
    """Aggregate wellness score (0–10) from recent logs."""
    if not health_logs:
        return None
    recent = health_logs[:14]  # last 14 entries
    scores = []
    for log in recent:
        s = 0
        count = 0
        if log.mood:
            s += log.mood; count += 1
        if log.energyLevel:
            s += log.energyLevel; count += 1
        if log.sleepHours:
            sleep_score = min(10, log.sleepHours / 8 * 10)
            s += sleep_score; count += 1
        if log.painLevel is not None:
            s += (10 - log.painLevel); count += 1
        if log.stressLevel:
            s += (10 - log.stressLevel); count += 1
        if count > 0:
            scores.append(s / count)
    return round(float(np.mean(scores)), 1) if scores else None


async def generate_insights(req: HealthInsightsRequest) -> HealthInsightsResponse:
    insights: List[InsightItem] = []
    anomalies: List[str] = []
    lifestyle_recommendations: List[str] = []

    health_logs = req.healthLogs
    meal_logs = req.mealLogs
    exercise_logs = req.exerciseLogs
    conditions = req.userProfile.conditions

    # ── 1. Trend Analysis ───────────────────────────────────────────────────
    moods = [l.mood for l in health_logs if l.mood]
    energies = [l.energyLevel for l in health_logs if l.energyLevel]
    sleeps = [l.sleepHours for l in health_logs if l.sleepHours is not None]

    energy_trend = _linear_trend(energies)
    sleep_trend = _linear_trend(sleeps)
    mood_trend = _linear_trend(moods)

    if mood_trend == "declining":
        insights.append(InsightItem(
            category="Mental Health",
            title="Declining Mood Trend",
            description="Your mood ratings have been consistently declining over recent logs.",
            severity="warning",
            recommendation="Consider mindfulness practices, social connection, or speaking with your healthcare provider."
        ))
    elif mood_trend == "improving":
        insights.append(InsightItem(
            category="Mental Health",
            title="Improving Mood Trend",
            description="Your mood has been trending upward — keep up the positive habits.",
            severity="info",
            recommendation="Identify which activities correlate with better mood and prioritise them."
        ))

    if sleep_trend == "declining":
        insights.append(InsightItem(
            category="Sleep",
            title="Reducing Sleep Duration",
            description="Your sleep hours have been decreasing recently.",
            severity="warning",
            recommendation="Aim for 7–9 hours. Maintain a consistent sleep schedule and limit screen time before bed."
        ))

    avg_sleep = np.mean(sleeps) if sleeps else None
    if avg_sleep and avg_sleep < 6:
        insights.append(InsightItem(
            category="Sleep",
            title="Consistently Low Sleep",
            description=f"Average sleep is {avg_sleep:.1f} hours — below the recommended 7–9 hours.",
            severity="alert",
            recommendation="Prioritise sleep hygiene. Discuss persistent sleep issues with your doctor."
        ))
        lifestyle_recommendations.append("Set a consistent bedtime and wake time, even on weekends.")

    # ── 2. Anomaly Detection ────────────────────────────────────────────────
    if len(energies) >= 4:
        anomaly_indices = _detect_anomalies_isolation(energies)
        if anomaly_indices:
            anomalies.append(f"Unusual energy level detected on {len(anomaly_indices)} occasion(s).")
            insights.append(InsightItem(
                category="Energy",
                title="Energy Level Anomaly Detected",
                description="One or more days had unusually low or high energy compared to your baseline.",
                severity="warning",
                recommendation="Review activities, sleep, and meals on those days to identify triggers."
            ))

    # ── 3. Symptom Pattern Analysis ─────────────────────────────────────────
    symptom_patterns, top_symptoms = _symptom_patterns(health_logs)
    if top_symptoms:
        insights.append(InsightItem(
            category="Symptoms",
            title=f"Frequent Symptoms: {', '.join(top_symptoms[:3])}",
            description=f"Recurring symptoms detected across your health logs.",
            severity="warning",
            recommendation="Document timing and potential triggers. Share this pattern with your care team."
        ))

    # ── 4. Correlations ─────────────────────────────────────────────────────
    sleep_mood_note = _sleep_mood_correlation(health_logs)
    if sleep_mood_note:
        insights.append(InsightItem(
            category="Correlation",
            title="Sleep–Mood Relationship",
            description=sleep_mood_note,
            severity="info",
            recommendation="Track sleep quality (not just hours) alongside mood for deeper insight."
        ))

    exercise_energy_note = _exercise_energy_correlation(exercise_logs, health_logs)
    if exercise_energy_note:
        insights.append(InsightItem(
            category="Exercise",
            title="Exercise Boosts Energy",
            description=exercise_energy_note,
            severity="info",
            recommendation="Maintain your exercise habit — it's clearly benefiting your daily energy."
        ))

    # ── 5. Meal Insights ────────────────────────────────────────────────────
    if meal_logs:
        calories_list = [m.calories for m in meal_logs if m.calories]
        if calories_list:
            avg_cal = int(np.mean(calories_list))
            if avg_cal < 1200:
                insights.append(InsightItem(
                    category="Nutrition",
                    title="Low Calorie Intake",
                    description=f"Average daily calories appear low (~{avg_cal} kcal).",
                    severity="warning",
                    recommendation="Ensure you're meeting minimum calorie needs. Consult a dietitian."
                ))
        meal_count = len(meal_logs)
        if meal_count < len(health_logs) * 0.5:
            lifestyle_recommendations.append("Increase meal logging frequency for more personalised insights.")
    else:
        lifestyle_recommendations.append("Start logging meals to unlock nutrition-based insights.")

    # ── 6. Exercise Insights ────────────────────────────────────────────────
    if not exercise_logs:
        insights.append(InsightItem(
            category="Exercise",
            title="No Exercise Logged",
            description="No exercise has been recorded recently.",
            severity="warning",
            recommendation="Even light daily movement (10–15 min walk) can significantly improve health outcomes."
        ))
    else:
        total_exercise_days = len(set(
            e.date[:10] for e in exercise_logs if e.date
        ))
        if total_exercise_days < 3:
            lifestyle_recommendations.append("Aim for at least 3 exercise sessions per week.")

    # ── 7. Condition-specific Insights ──────────────────────────────────────
    conditions_lower = [c.lower() for c in conditions]
    if any("diabet" in c for c in conditions_lower):
        lifestyle_recommendations.append("Monitor blood glucose before and after exercise.")
        lifestyle_recommendations.append("Distribute carbohydrate intake evenly across meals.")
    if any("hypertens" in c for c in conditions_lower):
        lifestyle_recommendations.append("Limit sodium intake; monitor BP regularly.")
    if any("cardiac" in c or "heart" in c for c in conditions_lower):
        lifestyle_recommendations.append("Follow cardiac rehabilitation guidelines for exercise.")

    if not lifestyle_recommendations:
        lifestyle_recommendations.append("Maintain consistent logging for more personalised insights.")

    wellness_score = _compute_wellness_score(health_logs)

    return HealthInsightsResponse(
        insights=insights,
        energyTrend=energy_trend,
        sleepTrend=sleep_trend,
        symptomPatterns=symptom_patterns,
        lifestyleRecommendations=lifestyle_recommendations,
        anomaliesDetected=anomalies,
        overallWellnessScore=wellness_score
    )
