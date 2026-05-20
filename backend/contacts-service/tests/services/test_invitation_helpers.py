from uuid import uuid4

from app.services.invitation_service import _build_canonical_user_pair


def test_build_canonical_user_pair_orders_uuids_consistently():
    user_a = uuid4()
    user_b = uuid4()

    low_id, high_id = _build_canonical_user_pair(
        user_a,
        user_b,
    )

    assert low_id < high_id
    assert {low_id, high_id} == {user_a, user_b}


def test_build_canonical_user_pair_is_order_independent():
    user_a = uuid4()
    user_b = uuid4()

    pair_one = _build_canonical_user_pair(
        user_a,
        user_b,
    )

    pair_two = _build_canonical_user_pair(
        user_b,
        user_a,
    )

    assert pair_one == pair_two
    