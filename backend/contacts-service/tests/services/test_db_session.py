from sqlalchemy import text


async def test_db_session_fixture_can_execute_queries(
    db_session,
):
    result = await db_session.execute(
        text("SELECT 1"),
    )

    value = result.scalar_one()

    assert value == 1
    