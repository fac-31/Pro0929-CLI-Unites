from __future__ import annotations

import rich_click as click

from ..core import (
    console,
    print_error,
    print_success,
    print_warning,
    ConfigManager,
    get_email_service,
)


@click.group(name="email")
def email_group() -> None:
    """Configure email delivery for invitations."""


@email_group.command("setup")
@click.option("--service", type=click.Choice(["resend"], case_sensitive=False), default="resend", show_default=True)
@click.option("--api-key", help="API key for the selected provider")
@click.option("--from-address", help="From email address")
@click.option("--from-name", default="CLI-Unites", show_default=True, help="Display name for outgoing emails")
def setup_email(service: str, api_key: str | None, from_address: str | None, from_name: str) -> None:
    """Configure the email provider used for team invitations."""
    manager = ConfigManager()

    if service.lower() != "resend":
        print_error(f"Email service '{service}' is not supported yet.")
        return

    if not api_key:
        api_key = click.prompt("Enter your Resend API key", hide_input=True)

    if not from_address:
        from_address = click.prompt("Enter the email address messages should come from")

    updates = {
        "email_service": "resend",
        "resend_api_key": api_key,
        "email_from_address": from_address,
        "email_from_name": from_name,
        "email_notifications_enabled": True,
        "email_templates_enabled": True,
    }
    manager.update(updates)

    print_success("Email service configured! Invitations will now attempt to send emails.")


@email_group.command("disable")
def disable_email() -> None:
    """Disable email notifications."""
    manager = ConfigManager()
    manager.update(
        {
            "email_notifications_enabled": False,
        }
    )
    print_warning("Email notifications disabled. Invites will still show the code in the CLI.")


@email_group.command("status")
def email_status() -> None:
    """Show the current email configuration."""
    manager = ConfigManager()
    enabled = manager.get("email_notifications_enabled", False)
    service_type = manager.get("email_service", "none")
    from_address = manager.get("email_from_address")
    from_name = manager.get("email_from_name")

    console.print(f"Email Service: {service_type}")
    console.print(f"Enabled: {'Yes' if enabled else 'No'}")
    console.print(f"From Address: {from_address or 'Not set'}")
    console.print(f"From Name: {from_name or 'CLI-Unites'}")


@email_group.command("test")
@click.option("--to", help="Email address to send a test invite to")
def test_email(to: str | None) -> None:
    """Send a test invitation email."""
    service = get_email_service()
    if not service:
        print_error("Email service not configured. Run 'notes email setup' first.")
        return

    if not to:
        to = click.prompt("Enter the email address to send a test invitation to")

    success = service.send_invitation_email(
        email=to,
        team_name="Test Team",
        inviter_name="CLI-Unites",
        invite_code="TEST01",
    )

    if success:
        print_success(f"Test invitation sent to {to}.")
    else:
        print_error("Failed to send test email. Check your configuration.")
