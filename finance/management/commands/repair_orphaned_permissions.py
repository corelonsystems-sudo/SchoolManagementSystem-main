"""
Repair auth_permission rows whose django_content_type row no longer exists.

These orphans block any SQLite table rebuild (i.e. most migrations), because
SQLite defers foreign-key enforcement and Django runs a full constraint check
at the end of the schema editor block.

Group grants pointing at an orphan are remapped to the equivalent live
permission (matched on codename + app_label) so no access is lost, then the
dead rows are removed.

Usage:
    python manage.py repair_orphaned_permissions --dry-run
    python manage.py repair_orphaned_permissions
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Remap and delete auth_permission rows with a missing content type."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT p.id, p.codename, p.content_type_id "
                "FROM auth_permission p "
                "LEFT JOIN django_content_type ct ON ct.id = p.content_type_id "
                "WHERE ct.id IS NULL "
                "ORDER BY p.id"
            )
            orphans = cursor.fetchall()

            if not orphans:
                self.stdout.write(self.style.SUCCESS("No orphaned permissions found."))
                return

            self.stdout.write("Found %d orphaned permission(s)." % len(orphans))

            # Live permissions keyed by codename. Orphans here are all finance
            # models whose content types were recreated with new ids, so the
            # codename is a reliable match.
            cursor.execute(
                "SELECT p.codename, p.id, ct.app_label "
                "FROM auth_permission p "
                "JOIN django_content_type ct ON ct.id = p.content_type_id"
            )
            live = {}
            for codename, perm_id, app_label in cursor.fetchall():
                live.setdefault(codename, (perm_id, app_label))

            remapped = 0
            dropped_links = 0
            unmatched = []

            for perm_id, codename, dead_ct in orphans:
                replacement = live.get(codename)

                cursor.execute(
                    "SELECT group_id FROM auth_group_permissions WHERE permission_id = %s",
                    [perm_id],
                )
                group_ids = [row[0] for row in cursor.fetchall()]

                if replacement is None:
                    if group_ids:
                        unmatched.append((codename, len(group_ids)))
                    continue

                new_perm_id, app_label = replacement

                for group_id in group_ids:
                    # Skip if the group already holds the live permission,
                    # otherwise the unique (group, permission) pair would clash.
                    cursor.execute(
                        "SELECT 1 FROM auth_group_permissions "
                        "WHERE group_id = %s AND permission_id = %s",
                        [group_id, new_perm_id],
                    )
                    already_held = cursor.fetchone() is not None

                    if dry_run:
                        action = "drop duplicate" if already_held else "remap"
                        self.stdout.write(
                            "  group %s: %s %s.%s (perm %s -> %s)"
                            % (group_id, action, app_label, codename, perm_id, new_perm_id)
                        )
                    elif already_held:
                        cursor.execute(
                            "DELETE FROM auth_group_permissions "
                            "WHERE group_id = %s AND permission_id = %s",
                            [group_id, perm_id],
                        )
                    else:
                        cursor.execute(
                            "UPDATE auth_group_permissions SET permission_id = %s "
                            "WHERE group_id = %s AND permission_id = %s",
                            [new_perm_id, group_id, perm_id],
                        )

                    if already_held:
                        dropped_links += 1
                    else:
                        remapped += 1

            if unmatched:
                self.stdout.write(
                    self.style.WARNING(
                        "No live equivalent for: "
                        + ", ".join("%s (%d group grants)" % u for u in unmatched)
                    )
                )

            orphan_ids = [row[0] for row in orphans]
            placeholders = ",".join(["%s"] * len(orphan_ids))

            if dry_run:
                self.stdout.write(
                    "\nDry run: would remap %d grant(s), drop %d duplicate(s), "
                    "delete %d permission row(s)."
                    % (remapped, dropped_links, len(orphan_ids))
                )
                return

            with transaction.atomic():
                cursor.execute(
                    "DELETE FROM auth_user_user_permissions WHERE permission_id IN (%s)"
                    % placeholders,
                    orphan_ids,
                )
                cursor.execute(
                    "DELETE FROM auth_group_permissions WHERE permission_id IN (%s)"
                    % placeholders,
                    orphan_ids,
                )
                cursor.execute(
                    "DELETE FROM auth_permission WHERE id IN (%s)" % placeholders,
                    orphan_ids,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Remapped %d grant(s), dropped %d duplicate(s), deleted %d dead permission row(s)."
                % (remapped, dropped_links, len(orphan_ids))
            )
        )
