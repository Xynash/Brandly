from app.services.ratelimit import SlidingWindowLimiter


def test_allows_up_to_the_limit_then_blocks_with_a_wait_time():
    lim = SlidingWindowLimiter(60)
    assert [lim.hit("a", 3, now=t) for t in (0, 1, 2)] == [None, None, None]
    assert lim.hit("a", 3, now=3) == 57  # the hit at t=0 frees up at t=60


def test_the_window_slides():
    lim = SlidingWindowLimiter(60)
    for t in (0, 1, 2):
        lim.hit("a", 3, now=t)
    assert lim.hit("a", 3, now=59) is not None
    assert lim.hit("a", 3, now=60) is None


def test_keys_are_independent():
    lim = SlidingWindowLimiter(60)
    assert lim.hit("a", 1, now=0) is None
    assert lim.hit("a", 1, now=1) is not None
    assert lim.hit("b", 1, now=1) is None


def test_zero_limit_blocks_everything():
    assert SlidingWindowLimiter(60).hit("a", 0, now=0) is not None
