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


def test_decoded_pts_drops_the_pre_roll_of_a_cut_clip():
    # a `-c copy` cut keeps packets from the keyframe before -ss with negative pts;
    # the decoder (edit list) never outputs them
    from snatch.video import decoded_pts
    pts = np.array([-0.0125, 0.0, -0.00833, 0.00417, -0.00417, 0.00833])
    np.testing.assert_allclose(decoded_pts(pts), [0.0, 0.00417, 0.00833])
    np.testing.assert_allclose(decoded_pts(np.array([0.1, 0.0])), [0.0, 0.1])
