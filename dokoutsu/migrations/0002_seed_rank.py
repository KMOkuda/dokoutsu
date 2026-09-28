from django.db import migrations

KYU_LABELS = [f"{i}級" for i in range(1, 16)]  # 1級, 2級, ..., 15級
DAN_LABELS = ["初段"] + [f"{i}段" for i in range(2, 9)]  # 初段, 2段, ..., 8段


def seed_ranks(apps, schema_editor):
    Rank = apps.get_model("dokoutsu", "Rank")
    order = 1
    for label in KYU_LABELS:
        Rank.objects.create(label=label, category="kyu", sort_order=order)
        order += 1
    for label in DAN_LABELS:
        Rank.objects.create(label=label, category="dan", sort_order=order)
        order += 1


def remove_ranks(apps, schema_editor):
    Rank = apps.get_model("dokoutsu", "Rank")
    Rank.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("dokoutsu", "0001_initial")]
    operations = [migrations.RunPython(seed_ranks, remove_ranks)]
