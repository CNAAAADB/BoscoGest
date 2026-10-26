from datetime import date, timedelta

import pytest

from app.models.entity_model import Entity
from app.models.membership_model import Membership
from app.models.notification_model import Notification
from app.models.role_model import Role
from app.models.user_model import User
from app.utils.auth import create_access_token, get_password_hash


def _notif_count(db_session, recipient_id, event_type):
    return (
        db_session.query(Notification)
        .filter(Notification.recipient_id == recipient_id, Notification.event_type == event_type)
        .count()
    )


# ── Helpers / fixtures ────────────────────────────────────────────────────────

def _make_socio(db_session, entity, email, name, surname):
    tag = email.split("@")[0]
    user = User(
        email=email,
        password_hash=get_password_hash("testpassword"),
        name=name,
        surname=surname,
        phone=f"6000{abs(hash(tag)) % 100000:05d}",
        birthdate=date(1990, 1, 1),
        dni=f"{abs(hash(tag)) % 100000000:08d}Z",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    socio_role = db_session.query(Role).filter(Role.name == "socio").first()
    membership = Membership(
        user_id=user.id, entity_id=entity.id, role_id=socio_role.id, is_active=True
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_entity(db_session, test_entity):
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    entity = Entity(name="Second Org", level=1)
    db_session.add(entity)
    db_session.flush()
    entity.roles.append(admin_role)
    db_session.commit()
    db_session.refresh(entity)
    return entity


def _create_fee(client, headers, entity_ids, name="Cuota socio", amount=50.0, periodicity="annual"):
    return client.post(
        "/fees",
        headers=headers,
        json={
            "name": name,
            "periodicity": periodicity,
            "entity_ids": entity_ids,
            "amount": amount,
            "valid_from": str(date.today() - timedelta(days=1)),
            "valid_until": None,
        },
    )


# ── Fees ────────────────────────────────────────────────────────────────────

def test_create_fee_single_entity(client, auth_headers, test_entity):
    resp = _create_fee(client, auth_headers, [test_entity.id])
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Cuota socio"
    assert data[0]["periodicity"] == "annual"
    assert data[0]["entity_id"] == test_entity.id
    assert data[0]["current_config"]["amount"] == 50.0


def test_create_fee_multiple_entities_creates_independent_copies(
    client, auth_headers, test_entity, second_entity, test_membership, db_session
):
    # Give the admin user a membership (admin role) in the second entity too.
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    db_session.add(
        Membership(
            user_id=test_membership.user_id,
            entity_id=second_entity.id,
            role_id=admin_role.id,
            is_active=True,
        )
    )
    db_session.commit()

    resp = _create_fee(client, auth_headers, [test_entity.id, second_entity.id])
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data) == 2
    entity_ids = {f["entity_id"] for f in data}
    assert entity_ids == {test_entity.id, second_entity.id}
    # Independent fees with distinct ids
    assert data[0]["id"] != data[1]["id"]


def test_create_fee_forbidden_when_no_permission_on_entity(
    client, auth_headers, test_entity, second_entity
):
    # User has no membership in second_entity → 403, and nothing is created.
    resp = _create_fee(client, auth_headers, [test_entity.id, second_entity.id])
    assert resp.status_code == 403
    listed = client.get(
        f"/fees?entity_id={test_entity.id}", headers=auth_headers
    ).json()
    assert listed == []


def test_list_fees(client, auth_headers, test_entity):
    _create_fee(client, auth_headers, [test_entity.id], name="Cuota A")
    _create_fee(client, auth_headers, [test_entity.id], name="Cuota B")
    resp = client.get(f"/fees?entity_id={test_entity.id}", headers=auth_headers)
    assert resp.status_code == 200
    names = sorted(f["name"] for f in resp.json())
    assert names == ["Cuota A", "Cuota B"]


def test_add_version_auto_closes_previous(client, auth_headers, test_entity):
    # First version: valid_from yesterday, open-ended (valid_until null = current).
    fee_id = _create_fee(client, auth_headers, [test_entity.id], amount=50.0).json()[0]["id"]

    # New version effective today; the previous one must be auto-closed.
    resp = client.post(
        f"/fees/{fee_id}/versions",
        headers=auth_headers,
        json={"amount": 75.0, "valid_from": str(date.today()), "valid_until": None},
    )
    assert resp.status_code == 201, resp.text

    history = client.get(f"/fees/{fee_id}/history", headers=auth_headers).json()
    assert len(history) == 2
    # History ordered desc by valid_from: [new (open), old (auto-closed)]
    newest, previous = history[0], history[1]
    assert newest["amount"] == 75.0 and newest["valid_until"] is None
    assert previous["amount"] == 50.0
    assert previous["valid_until"] == str(date.today() - timedelta(days=1))  # closed day before new

    fees = client.get(f"/fees?entity_id={test_entity.id}", headers=auth_headers).json()
    current = next(f for f in fees if f["id"] == fee_id)
    assert current["current_config"]["amount"] == 75.0


# ── Assignments ───────────────────────────────────────────────────────────────

def test_members_preview(client, auth_headers, test_entity, db_session, test_membership):
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")

    # No period param: derived from the fee's periodicity (annual) + today
    resp = client.get(
        f"/fees/members-preview?fee_id={fee_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    members = {m["user_id"]: m for m in resp.json()}
    assert socio.id in members
    assert members[socio.id]["role_name"] == "socio"
    assert members[socio.id]["already_assigned"] is False


def _subscribe(client, headers, fee_id, user_ids, exempt=False, reason=None):
    """Enrol members in a fee.

    Generation reads this roster rather than taking an arbitrary list of user
    ids, so a test has to enrol before it can charge.
    """
    body = {"user_ids": user_ids, "exempt": exempt}
    if reason:
        body["exempt_reason"] = reason
    resp = client.post(f"/fees/{fee_id}/subscriptions", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_generate_selective_and_idempotent(
    client, auth_headers, test_entity, db_session, test_membership
):
    fee_id = _create_fee(client, auth_headers, [test_entity.id], amount=50.0).json()[0]["id"]
    s1 = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")
    s2 = _make_socio(db_session, test_entity, "s2@example.com", "Beto", "López")
    expected_period = str(date.today().year)  # annual fee, calendar cycle → the year
    _subscribe(client, auth_headers, fee_id, [s1.id, s2.id])

    # Both are enrolled; user_ids narrows this run to s1 only.
    resp = client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id, "user_ids": [s1.id]},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"] == 1
    assert resp.json()["period"] == expected_period

    assignments = client.get(
        f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers
    ).json()
    assert len(assignments) == 1
    assert assignments[0]["user_id"] == s1.id
    assert assignments[0]["amount"] == 50.0
    assert assignments[0]["periodicity"] == "annual"
    assert assignments[0]["period"] == expected_period
    assert assignments[0]["fee_name"] == "Cuota socio"

    # Re-run: s1 is already charged for this period (skip), s2 is not (create)
    resp2 = client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id, "user_ids": [s1.id, s2.id]},
    )
    assert resp2.status_code == 201
    body = resp2.json()
    assert body["created"] == 1 and body["skipped"] == 1

    # Preview now marks s1/s2 as already assigned
    preview = client.get(
        f"/fees/members-preview?fee_id={fee_id}", headers=auth_headers
    ).json()
    flags = {m["user_id"]: m["already_assigned"] for m in preview}
    assert flags[s1.id] is True and flags[s2.id] is True


def test_generate_requires_current_version(client, auth_headers, test_entity, db_session):
    # Fee whose only version is in the future → no current amount → 422
    resp = client.post(
        "/fees",
        headers=auth_headers,
        json={
            "name": "Futura",
            "periodicity": "monthly",
            "entity_ids": [test_entity.id],
            "amount": 30.0,
            "valid_from": str(date.today() + timedelta(days=10)),
            "valid_until": None,
        },
    )
    fee_id = resp.json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s3@example.com", "Caro", "Ruiz")
    _subscribe(client, auth_headers, fee_id, [socio.id])

    gen = client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id, "user_ids": [socio.id]},
    )
    assert gen.status_code == 422


def test_update_assignment_status_sets_paid_at(
    client, auth_headers, test_entity, db_session, test_membership
):
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")
    _subscribe(client, auth_headers, fee_id, [socio.id])
    client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id, "user_ids": [socio.id]},
    )
    assignment_id = client.get(
        f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers
    ).json()[0]["id"]

    resp = client.patch(
        f"/fees/assignments/{assignment_id}/status",
        headers=auth_headers,
        json={"status": "paid"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "paid"
    assert data["paid_at"] is not None


def test_paid_notifies_member(client, auth_headers, test_entity, db_session, test_membership):
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")
    _subscribe(client, auth_headers, fee_id, [socio.id])
    client.post("/fees/assignments/generate", headers=auth_headers,
                json={"fee_id": fee_id, "user_ids": [socio.id]})
    aid = client.get(f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers).json()[0]["id"]

    client.patch(f"/fees/assignments/{aid}/status", headers=auth_headers, json={"status": "paid"})
    assert _notif_count(db_session, socio.id, "fee_paid") == 1


# ── Maintenance ───────────────────────────────────────────────────────────────

def _create_fee_json(client, headers, entity_id, **overrides):
    body = {
        "name": "Cuota", "periodicity": "annual", "entity_ids": [entity_id],
        "amount": 50.0, "valid_from": str(date.today() - timedelta(days=1)), "valid_until": None,
    }
    body.update(overrides)
    return client.post("/fees", headers=headers, json=body)


def test_maintenance_marks_overdue_and_notifies(
    client, auth_headers, test_entity, db_session, test_membership
):
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")
    _subscribe(client, auth_headers, fee_id, [socio.id])
    # Assignment already past its due date
    client.post("/fees/assignments/generate", headers=auth_headers,
                json={"fee_id": fee_id, "user_ids": [socio.id],
                      "due_date": str(date.today() - timedelta(days=1))})

    resp = client.post("/fees/maintenance/run", headers=auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "success"
    assert resp.json()["overdue_count"] >= 1

    assignment = client.get(f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers).json()[0]
    assert assignment["status"] == "overdue"
    assert _notif_count(db_session, socio.id, "fee_overdue") == 1


def test_maintenance_sends_reminder_once(
    client, auth_headers, test_entity, db_session, test_membership
):
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")
    _subscribe(client, auth_headers, fee_id, [socio.id])
    # Due in 3 days → within the default 7-day reminder window, not overdue
    client.post("/fees/assignments/generate", headers=auth_headers,
                json={"fee_id": fee_id, "user_ids": [socio.id],
                      "due_date": str(date.today() + timedelta(days=3))})

    r1 = client.post("/fees/maintenance/run", headers=auth_headers).json()
    assert r1["reminded_count"] >= 1
    assert _notif_count(db_session, socio.id, "fee_reminder") == 1

    # Second run must not re-send the reminder (reminder_sent guard)
    client.post("/fees/maintenance/run", headers=auth_headers)
    assert _notif_count(db_session, socio.id, "fee_reminder") == 1


def test_maintenance_auto_renews_carry_over(
    client, auth_headers, test_entity, db_session, test_membership
):
    # Annual fee with auto-renew on
    fee_id = _create_fee_json(client, auth_headers, test_entity.id, auto_renew=True).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "s1@example.com", "Ana", "García")
    _subscribe(client, auth_headers, fee_id, [socio.id])
    last_year = date.today().year - 1
    # A charge in the previous period, to show renewal no longer depends on it
    client.post("/fees/assignments/generate", headers=auth_headers,
                json={"fee_id": fee_id, "user_ids": [socio.id],
                      "reference_date": f"{last_year}-06-01"})

    resp = client.post("/fees/maintenance/run", headers=auth_headers).json()
    assert resp["renewed_count"] >= 1

    periods = {a["period"] for a in
               client.get(f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers).json()
               if a["user_id"] == socio.id}
    assert str(date.today().year) in periods  # renewed into the current period
    assert _notif_count(db_session, socio.id, "fee_renewed") == 1

    # Idempotent: second run does not renew again
    resp2 = client.post("/fees/maintenance/run", headers=auth_headers).json()
    assert resp2["renewed_count"] == 0


def test_maintenance_records_run_and_lists(client, auth_headers, test_entity):
    client.post("/fees/maintenance/run", headers=auth_headers)
    runs = client.get("/fees/maintenance/runs", headers=auth_headers)
    assert runs.status_code == 200
    assert len(runs.json()) >= 1
    assert runs.json()[0]["trigger"] == "manual"


def test_maintenance_requires_permission(client, db_session, test_entity, test_membership):
    socio = _make_socio(db_session, test_entity, "nosey@example.com", "Sin", "Permiso")
    token = create_access_token({"sub": str(socio.id)})
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/fees/maintenance/run", headers=headers).status_code == 403
    assert client.get("/fees/maintenance/runs", headers=headers).status_code == 403


# ── Enrolments, exemptions and shifted yearly cycles ────────────────────────
#
# These cover the three problems the fee audit turned up: renewal that broke
# when a period was skipped, no way to record a member who owes nothing, and
# yearly periods whose label depended on the day they were generated.


def test_renewal_survives_a_skipped_period(
    client, auth_headers, test_entity, db_session, test_membership
):
    """Renewal reads the enrolments, not the previous period's charges.

    It used to copy whoever was billed last period, so a period nobody
    generated left the next one with nothing to copy — the fee stopped
    renewing silently and never resumed.
    """
    from app.services.fee_service import FeeService

    fee_id = _create_fee_json(
        client, auth_headers, test_entity.id, auto_renew=True
    ).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "skip@example.com", "Ana", "García")
    _subscribe(client, auth_headers, fee_id, [socio.id])

    # Charge two years ago, then leave last year completely ungenerated.
    two_years_ago = date.today().year - 2
    client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id, "user_ids": [socio.id],
              "reference_date": f"{two_years_ago}-06-01"},
    )

    service = FeeService(db_session)
    run = service.run_maintenance(today=date.today())

    assert run.renewed_count >= 1, (
        "the gap in the charge history stopped renewal; it should depend only "
        "on the enrolment"
    )
    periods = {
        a["period"]
        for a in client.get(
            f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers
        ).json()
    }
    assert str(date.today().year) in periods


def test_exempt_member_is_recorded_owing_nothing(
    client, auth_headers, test_entity, db_session, test_membership
):
    """An honorary member (REQ-USR-02) is covered but not charged.

    Deliberately distinct from cancelling the charge, which reads as billed by
    mistake, and from unenrolling, which loses them from the roster.
    """
    fee_id = _create_fee(client, auth_headers, [test_entity.id], amount=40.0).json()[0]["id"]
    payer = _make_socio(db_session, test_entity, "pays@example.com", "Luis", "Pérez")
    honorary = _make_socio(db_session, test_entity, "honor@example.com", "Rosa", "Muñoz")

    _subscribe(client, auth_headers, fee_id, [payer.id])
    _subscribe(client, auth_headers, fee_id, [honorary.id],
               exempt=True, reason="Socia de honor")

    result = client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id},
    ).json()

    assert result["created"] == 1
    assert result["exempt"] == 1

    rows = {
        a["user_id"]: a
        for a in client.get(
            f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers
        ).json()
    }
    assert rows[payer.id]["status"] == "pending"
    assert float(rows[payer.id]["amount"]) == 40.0
    # Present in the period's roster rather than absent from it.
    assert rows[honorary.id]["status"] == "exempt"
    assert float(rows[honorary.id]["amount"]) == 0.0
    assert rows[honorary.id]["notes"] == "Socia de honor"


def test_ending_an_enrolment_stops_future_charges(
    client, auth_headers, test_entity, db_session, test_membership
):
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    socio = _make_socio(db_session, test_entity, "leaves@example.com", "Iván", "Ruiz")
    _subscribe(client, auth_headers, fee_id, [socio.id])

    resp = client.request(
        "DELETE",
        f"/fees/{fee_id}/subscriptions/{socio.id}",
        headers=auth_headers,
        json={"ends_on": str(date.today() - timedelta(days=1))},
    )
    assert resp.status_code == 204

    result = client.post(
        "/fees/assignments/generate", headers=auth_headers, json={"fee_id": fee_id}
    ).json()
    assert result["created"] == 0


def test_generation_only_reaches_enrolled_members(
    client, auth_headers, test_entity, db_session, test_membership
):
    """user_ids narrows the roster; it cannot introduce somebody outside it.

    Accepting an arbitrary list is what let the set of payers drift from one
    period to the next.
    """
    fee_id = _create_fee(client, auth_headers, [test_entity.id]).json()[0]["id"]
    enrolled = _make_socio(db_session, test_entity, "in@example.com", "Eva", "Soto")
    outsider = _make_socio(db_session, test_entity, "out@example.com", "Hugo", "Lara")
    _subscribe(client, auth_headers, fee_id, [enrolled.id])

    result = client.post(
        "/fees/assignments/generate",
        headers=auth_headers,
        json={"fee_id": fee_id, "user_ids": [enrolled.id, outsider.id]},
    ).json()

    assert result["created"] == 1
    charged = {
        a["user_id"]
        for a in client.get(
            f"/fees/assignments?entity_id={test_entity.id}", headers=auth_headers
        ).json()
    }
    assert outsider.id not in charged


def test_annual_period_follows_the_cycle_start_month_when_configured():
    """A September-to-August cycle, labelled by the two years it spans.

    Anchored to the calendar year, the same cycle came out as one year or the
    next depending on the day it was generated, and two consecutive cycles
    could collide on the same label — which the unique constraint would then
    reject.
    """
    from app.services.fee_service import derive_period, period_end_date

    october = date(2026, 10, 15)
    january = date(2027, 1, 20)
    june = date(2027, 6, 1)
    next_cycle = date(2027, 9, 2)

    assert derive_period("annual", october, 9) == "2026-2027"
    assert derive_period("annual", january, 9) == "2026-2027"
    assert derive_period("annual", june, 9) == "2026-2027"
    assert derive_period("annual", next_cycle, 9) == "2027-2028"

    # Due at the end of the cycle, not in the middle of it.
    assert period_end_date("annual", january, 9) == date(2027, 8, 31)

    # A calendar cycle is unchanged.
    assert derive_period("annual", june, 1) == "2027"
    assert period_end_date("annual", june, 1) == date(2027, 12, 31)


def test_quarterly_periods_follow_the_shifted_cycle_too():
    from app.services.fee_service import derive_period

    assert derive_period("quarterly", date(2026, 9, 5), 9) == "2026-2027-T1"
    assert derive_period("quarterly", date(2026, 12, 20), 9) == "2026-2027-T2"
    assert derive_period("quarterly", date(2027, 7, 7), 9) == "2026-2027-T4"
