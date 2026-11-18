-- Fictional report template for offline parameter binding only.
DECLARE @StartDate datetime = ?;
DECLARE @EndDate datetime = ?;
DECLARE @FirstObservationId int;
DECLARE @LastObservationId int;

SELECT @FirstObservationId = MIN(ObservationId),
       @LastObservationId = MAX(ObservationId)
FROM dbo.DemoObservation
WHERE ObservedAt >= @StartDate
  AND ObservedAt < DATEADD(day, 1, CONVERT(date, @EndDate));

SELECT obs.ObservationId, obs.Label, PR.Name
FROM dbo.DemoObservation AS obs
JOIN dbo.DemoProduct AS PR ON PR.ProductId = obs.ProductId
WHERE obs.ObservationId BETWEEN @FirstObservationId AND @LastObservationId
  AND obs.Label NOT LIKE '%Comment%'
  AND PR.Name IN (/*PRODUCT_PARAMETERS*/);
