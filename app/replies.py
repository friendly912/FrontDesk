from .shops import ShopConfig


def build_auto_reply(shop: ShopConfig) -> str:
    lines = [f"We're open {shop.hours}."]
    if shop.services:
        lines.append(f"Services: {', '.join(shop.services)}.")
    lines.append(f"Book here: {shop.booking_link}")
    if shop.after_hours_note:
        lines.append(shop.after_hours_note)
    return " ".join(lines)
