import numpy as np
import pytest

from snatch.video import frame_times, mean_rate


def test_frame_times_reads_t_or_falls_back_to_the_tagged_rate():
    t = np.array([0, 1, 2, 5, 6]) / 240
    np.testing.assert_array_equal(frame_times({"t": t, "fps": np.asarray(240.0)}), t)
    old = {"keypoints": np.zeros((4, 17, 2)), "fps": np.asarray(240.0)}
    np.testing.assert_array_equal(frame_times(old), np.arange(4) / 240)


def test_mean_rate_counts_the_frames_actually_there():
    assert mean_rate(np.arange(241) / 240) == pytest.approx(240)
    keep = np.array([i for i in range(1201) if i % 6 != 5])  # 1 in 6 dropped
    assert mean_rate(keep / 240) == pytest.approx(200, abs=0.5)
