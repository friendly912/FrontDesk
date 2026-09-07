from app.replies import build_auto_reply
from app.shops import ShopConfig


def test_build_auto_reply_includes_hours_services_and_link():
    shop = ShopConfig(
        shop_id="test-shop",
        name="Test Shop",
        hours="Tue-Sat, 9-6",
        services=["Trim", "Color"],
        booking_link="https://example.com/book",
        google_sheet_id="sheet123",
        after_hours_note="A person picks this up after 9am.",
    )

    reply = build_auto_reply(shop)

    assert "Tue-Sat, 9-6" in reply
    assert "Trim" in reply and "Color" in reply
    assert "https://example.com/book" in reply
    assert "A person picks this up after 9am." in reply


def test_build_auto_reply_omits_empty_services_line():
    shop = ShopConfig(
        shop_id="test-shop",
        name="Test Shop",
        hours="Tue-Sat, 9-6",
        services=[],
        booking_link="https://example.com/book",
        google_sheet_id="sheet123",
    )

    reply = build_auto_reply(shop)

    assert "Services:" not in reply
