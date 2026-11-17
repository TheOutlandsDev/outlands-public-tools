DECLARE @StartDateTime datetime2 = ?;
DECLARE @EndDateExclusive datetime2 = ?;
DECLARE @MaxRows int = ?;

SELECT TOP (@MaxRows)
    mh.ItemName,
    mh.EventDateTime
FROM DemoManufacturing.dbo.DemoMovement AS mh
WHERE mh.EventDateTime >= @StartDateTime
  AND mh.EventDateTime < @EndDateExclusive
ORDER BY mh.EventDateTime;
