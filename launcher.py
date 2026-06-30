"""Gym ERP application entry point.

Usage:
    python launcher.py            # launch the desktop application
    python launcher.py --check    # headless self-test (bootstrap + DB probe); no GUI
    python launcher.py --version  # print version and exit

The launcher is the outermost layer: it builds the application context via the composition
root and starts the Qt event loop. A global exception hook guarantees that an unexpected error
is logged and reported instead of silently crashing the process (Part 1: *never crash*).
"""

from __future__ import annotations

import sys
from types import TracebackType

from app.core.constants import APP_NAME, APP_VERSION, ORG_DOMAIN, ORG_NAME
from app.infrastructure import ApplicationContext, bootstrap


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if "--version" in args:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    if "--check" in args:
        return _run_check()
    return _run_gui()


def _run_check() -> int:
    """Bootstrap and probe the database without starting the GUI (CI/diagnostics)."""
    context = bootstrap()
    try:
        ok = context.verify_database()
        print(f"{APP_NAME} {APP_VERSION}: bootstrap OK; database {'OK' if ok else 'FAILED'}")
        return 0 if ok else 1
    finally:
        context.dispose()


def _run_gui() -> int:
    from app.modules.attendance.setup import register_attendance_services
    from app.modules.audit.setup import register_audit_services
    from app.modules.employees.setup import register_employee_services
    from app.modules.expenses.setup import register_expense_services
    from app.modules.inventory.setup import initialize_inventory
    from app.modules.members.setup import register_members_services
    from app.modules.membership.setup import initialize_membership
    from app.modules.notifications.setup import register_notification_services
    from app.modules.payments.setup import initialize_payments
    from app.modules.reports.setup import register_report_services
    from app.modules.security.services import AuthenticationService
    from app.modules.security.setup import initialize_security
    from app.modules.security.ui.login_dialog import LoginDialog
    from app.modules.settings.setup import register_settings_services
    from app.modules.trainers.setup import register_trainer_services
    from app.themes.theme_manager import ThemeManager
    from app.widgets.main_window import MainWindow
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialog

    context = bootstrap()
    _install_exception_hook(context)
    # Create the schema and seed baselines before login, then register module services.
    initialize_security(context)
    register_members_services(context.container)
    initialize_membership(context)  # seeds default plans + registers the membership service
    register_attendance_services(context.container)
    initialize_payments(context)  # registers + auto-records subscription payments via events
    register_trainer_services(context.container)
    register_settings_services(context.container)
    initialize_inventory(context)  # seeds sample products + registers product/POS services
    register_report_services(context.container)
    register_employee_services(context.container)
    register_notification_services(context.container)
    register_expense_services(context.container)
    register_audit_services(context.container)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)
    app.setOrganizationDomain(ORG_DOMAIN)
    app.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if context.config.is_rtl else Qt.LayoutDirection.LeftToRight
    )

    from app.widgets.resources import app_icon_path
    from PySide6.QtGui import QIcon

    icon = app_icon_path()
    if icon is not None:
        app.setWindowIcon(QIcon(str(icon)))

    theme_manager = ThemeManager.from_config(context.config)
    theme_manager.apply(app)

    try:
        login = LoginDialog(
            authentication_service=context.container.resolve(AuthenticationService),
            localization=context.localization,
        )
        if login.exec() != QDialog.DialogCode.Accepted or login.authenticated_user is None:
            return 0  # user cancelled the login

        window = MainWindow(
            context,
            theme_manager,
            current_user=login.authenticated_user,
            nav_items=_nav_items(),
            kpi_items=_kpi_items(context),
        )
        window.show()
        return app.exec()
    finally:
        context.dispose()


def _nav_items() -> list:
    """Navigation contributions from business modules (extended as modules are added)."""
    from app.modules.attendance.ui.checkin_view import CheckInView
    from app.modules.audit.ui.audit_view import AuditView
    from app.modules.employees.ui.employees_view import EmployeesView
    from app.modules.expenses.ui.expenses_view import ExpensesView
    from app.modules.inventory.ui.pos_view import PosView
    from app.modules.inventory.ui.products_view import ProductsView
    from app.modules.members.ui.members_view import MembersView
    from app.modules.membership.ui.plans_view import PlansView
    from app.modules.membership.ui.subscriptions_view import SubscriptionsView
    from app.modules.notifications.ui.notifications_view import NotificationsView
    from app.modules.payments.ui.payments_view import PaymentsView
    from app.modules.reports.ui.reports_view import ReportsView
    from app.modules.security.permissions import Permissions
    from app.modules.settings.ui.settings_view import SettingsView
    from app.modules.trainers.ui.trainers_view import TrainersView
    from app.widgets.navigation import NavItem

    return [
        NavItem(
            "members",
            "nav.members",
            "👤",
            lambda c, u: MembersView(c, u),
            permission=Permissions.MEMBERS_VIEW,
            order=10,
        ),
        NavItem(
            "subscriptions",
            "nav.subscriptions",
            "🎟️",
            lambda c, u: SubscriptionsView(c, u),
            permission=Permissions.MEMBERSHIPS_VIEW,
            order=20,
        ),
        NavItem(
            "checkin",
            "nav.checkin",
            "✅",
            lambda c, u: CheckInView(c, u),
            permission=Permissions.ATTENDANCE_CHECKIN,
            order=30,
        ),
        NavItem(
            "pos",
            "nav.pos",
            "🛒",
            lambda c, u: PosView(c, u),
            permission=Permissions.POS_USE,
            order=35,
        ),
        NavItem(
            "payments",
            "nav.payments",
            "💵",
            lambda c, u: PaymentsView(c, u),
            permission=Permissions.PAYMENTS_VIEW,
            order=40,
        ),
        NavItem(
            "expenses",
            "nav.expenses",
            "🧾",
            lambda c, u: ExpensesView(c, u),
            permission=Permissions.EXPENSES_VIEW,
            order=42,
        ),
        NavItem(
            "trainers",
            "nav.trainers",
            "🏋️",
            lambda c, u: TrainersView(c, u),
            permission=Permissions.TRAINERS_VIEW,
            order=50,
        ),
        NavItem(
            "plans",
            "nav.plans",
            "🏷️",
            lambda c, u: PlansView(c, u),
            permission=Permissions.MEMBERSHIPS_MANAGE,
            order=60,
        ),
        NavItem(
            "products",
            "nav.products",
            "📦",
            lambda c, u: ProductsView(c, u),
            permission=Permissions.INVENTORY_VIEW,
            order=65,
        ),
        NavItem(
            "reports",
            "nav.reports",
            "📊",
            lambda c, u: ReportsView(c, u),
            permission=Permissions.REPORTS_VIEW,
            order=70,
        ),
        NavItem(
            "employees",
            "nav.employees",
            "🧑‍💼",
            lambda c, u: EmployeesView(c, u),
            permission=Permissions.EMPLOYEES_VIEW,
            order=75,
        ),
        NavItem(
            "notifications",
            "nav.notifications",
            "🔔",
            lambda c, u: NotificationsView(c, u),
            permission=Permissions.NOTIFICATIONS_VIEW,
            order=15,
        ),
        NavItem(
            "audit",
            "nav.audit",
            "📜",
            lambda c, u: AuditView(c, u),
            permission=Permissions.AUDIT_VIEW,
            order=80,
        ),
        NavItem(
            "settings",
            "nav.settings",
            "⚙️",
            lambda c, u: SettingsView(c, u),
            permission=Permissions.SETTINGS_MANAGE,
            order=90,
        ),
    ]


def _kpi_items(context: ApplicationContext) -> list:
    """Dashboard KPI cards computed from module services."""
    from app.core.pagination import PageRequest
    from app.modules.attendance.services import AttendanceService
    from app.modules.expenses.services import ExpenseService
    from app.modules.members.services import MemberService
    from app.modules.membership.services import MembershipService
    from app.modules.notifications.services import NotificationService
    from app.modules.payments.services import PaymentService
    from app.modules.security.permissions import Permissions
    from app.widgets.navigation import KpiCard

    members = context.container.resolve(MemberService)
    membership = context.container.resolve(MembershipService)
    attendance = context.container.resolve(AttendanceService)
    payments = context.container.resolve(PaymentService)
    notifications = context.container.resolve(NotificationService)
    expenses = context.container.resolve(ExpenseService)

    def _member_count() -> str:
        result = members.list_members(PageRequest(size=1))
        return str(result.value.total) if result.is_success else "—"

    def _net_profit() -> str:
        return f"{payments.total_revenue() - expenses.total_expenses():.2f}"

    return [
        KpiCard("kpi.members", "👥", _member_count, permission=Permissions.MEMBERS_VIEW, order=10),
        KpiCard(
            "kpi.active_subscriptions",
            "🎟️",
            lambda: str(membership.count_active_subscriptions()),
            permission=Permissions.MEMBERSHIPS_VIEW,
            order=20,
        ),
        KpiCard(
            "kpi.today_checkins",
            "✅",
            lambda: str(attendance.today_count()),
            permission=Permissions.ATTENDANCE_VIEW,
            order=30,
        ),
        KpiCard(
            "kpi.today_revenue",
            "💵",
            lambda: f"{payments.today_revenue():.2f}",
            permission=Permissions.PAYMENTS_VIEW,
            order=40,
        ),
        KpiCard(
            "kpi.total_revenue",
            "📈",
            lambda: f"{payments.total_revenue():.2f}",
            permission=Permissions.PAYMENTS_VIEW,
            order=50,
        ),
        KpiCard(
            "kpi.total_expenses",
            "🧾",
            lambda: f"{expenses.total_expenses():.2f}",
            permission=Permissions.EXPENSES_VIEW,
            order=55,
        ),
        KpiCard(
            "kpi.net_profit",
            "💰",
            _net_profit,
            permission=Permissions.EXPENSES_VIEW,
            order=58,
        ),
        KpiCard(
            "kpi.alerts",
            "🔔",
            lambda: str(notifications.count_alerts()),
            permission=Permissions.NOTIFICATIONS_VIEW,
            order=60,
        ),
    ]


def _install_exception_hook(context: ApplicationContext) -> None:
    """Route unhandled exceptions to the log and a dialog instead of crashing."""
    logger = context.logging.get_logger("app.launcher")

    def _hook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                QMessageBox.critical(
                    None,
                    f"{APP_NAME} — Unexpected Error",
                    "An unexpected error occurred. It has been logged.\n\n"
                    f"{exc_type.__name__}: {exc}",
                )
        except Exception:  # noqa: BLE001 - reporting must never raise
            pass

    sys.excepthook = _hook


if __name__ == "__main__":
    sys.exit(main())
