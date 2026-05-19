from gupiaofenxi.pipeline.historical_prediction import HistoricalPrediction, SimilaritySample


def test_historical_prediction_uses_similar_score_samples():
    prediction = HistoricalPrediction(
        samples=[
            SimilaritySample(score=70, next_day_return=1.0, three_day_return=2.5),
            SimilaritySample(score=72, next_day_return=-0.5, three_day_return=1.5),
            SimilaritySample(score=90, next_day_return=5.0, three_day_return=8.0),
        ],
        min_samples=2,
        score_band=3,
    ).estimate(score=71)

    assert prediction.sample_count == 2
    assert prediction.next_day_up_probability == 0.5
    assert prediction.three_day_up_probability == 1.0
    assert prediction.expected_return == 2.0
    assert prediction.source == "history"


def test_historical_prediction_falls_back_when_samples_are_insufficient():
    prediction = HistoricalPrediction(samples=[], min_samples=2).estimate(score=70)

    assert prediction.sample_count == 0
    assert prediction.source == "fallback"
    assert prediction.expected_return == 2.0
