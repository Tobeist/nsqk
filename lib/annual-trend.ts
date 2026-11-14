/** OLS on consecutive annual observations with a Bartlett HAC(3) covariance. */
export function annualTrend(values: number[]) {
  if (values.length < 20 || values.some((value) => !Number.isFinite(value))) {
    throw new Error("El índice anual requiere al menos veinte años consecutivos sin faltantes.");
  }
  const n = values.length;
  const center = (n - 1) / 2;
  const mean = values.reduce((sum, value) => sum + value, 0) / n;
  let sumTimeSquared = 0;
  let sumTimeValue = 0;
  for (let i = 0; i < n; i++) {
    const time = i - center;
    sumTimeSquared += time * time;
    sumTimeValue += time * (values[i] - mean);
  }
  const slopePerYear = sumTimeValue / sumTimeSquared;
  const scores = values.map((value, i) =>
    (i - center) * (value - mean - slopePerYear * (i - center)),
  );
  let longRunVariance = scores.reduce((sum, score) => sum + score * score, 0);
  for (let lag = 1; lag <= 3; lag++) {
    let cross = 0;
    for (let i = lag; i < n; i++) cross += scores[i] * scores[i - lag];
    longRunVariance += 2 * (1 - lag / 4) * cross;
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
