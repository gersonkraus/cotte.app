from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[1] / "cotte-frontend"


def test_briefing_today_has_mobile_overflow_guards():
    briefing_js = (FRONTEND / "js" / "tenant-comercial-briefing.js").read_text()

    assert "@media(max-width:560px)" in briefing_js
    assert ".briefing-card-header{flex-direction:column" in briefing_js
    assert ".briefing-actions>button{flex:1 1 140px" in briefing_js


def test_lead_detail_modal_has_mobile_overflow_guards():
    css = (FRONTEND / "css" / "tenant-comercial.css").read_text()

    assert "#modal-detail .modal" in css
    assert ".lead-detail-scroll" in css
    assert ".lead-tl-item" in css and "grid-template-columns:32px 1fr" in css
    assert ".lead-tl-time" in css and "grid-column:2" in css
    assert ".lead-note-composer" in css and "flex-direction:column" in css


def test_lead_create_modal_stays_above_mobile_tab_menu():
    css = (FRONTEND / "css" / "tenant-comercial.css").read_text()
    precision_css = (FRONTEND / "css" / "tenant-comercial-precision.css").read_text()

    assert "z-index: 10000" in precision_css
    assert ".modal-overlay" in css and "z-index: 11000" in css


def test_topbar_notification_button_is_protected_on_mobile():
    css = (FRONTEND / "css" / "tenant-comercial.css").read_text()
    api_js = (FRONTEND / "js" / "api.js").read_text()

    assert "topbar-notification-btn" in api_js
    assert "topbar-notification-badge" in api_js
    assert "#topbar-notificacoes .topbar-notification-btn" in css
    assert "width: 36px" in css
    assert "display: inline-flex" in css
