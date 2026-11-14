/** OLS with calendar-month effects and a Bartlett HAC(12) covariance. */
export function seasonalTrend(values: number[]) {
  if (values.length < 120 || values.length % 12 !== 0 || values.some((v) => !Number.isFinite(v))) {
    throw new Error("El ajuste requiere al menos diez años completos sin valores faltantes.");
  }

  const n = values.length;
  const monthMeans = Array.from({ length: 12 }, (_, month) => {
    let total = 0;
    for (let i = month; i < n; i += 12) total += values[i];
    return total / (n / 12);
  });
  const centeredTime = Array.from({ length: n }, (_, i) =>
    i / 12 - (n - 12) / 24 - (i % 12) / 12,
  );
  let sumTimeSquared = 0;
  let sumTimeValue = 0;
  for (let i = 0; i < n; i++) {
    sumTimeSquared += centeredTime[i] ** 2;
    sumTimeValue += centeredTime[i] * (values[i] - monthMeans[i % 12]);
  }
  const slopePerYear = sumTimeValue / sumTimeSquared;
  const scores = values.map((value, i) => {
    const residual = value - monthMeans[i % 12] - slopePerYear * centeredTime[i];
    return centeredTime[i] * residual;
  });
  let longRunVariance = scores.reduce((sum, score) => sum + score * score, 0);
  for (let lag = 1; lag <= 12; lag++) {
    let cross = 0;
    for (let i = lag; i < n; i++) cross += scores[i] * scores[i - lag];
    longRunVariance += 2 * (1 - lag / 13) * cross;
  }
  const slopePerDecade = 10 * slopePerYear;
  const standardErrorPerDecade = 10 * Math.sqrt(Math.max(0, longRunVariance)) / sumTimeSquared;
  const margin = 1.959963984540054 * standardErrorPerDecade;
  return {
    slopePerDecade,
    confidenceInterval: [slopePerDecade - margin, slopePerDecade + margin] as [number, number],
    sampleSize: n,
  };
}
