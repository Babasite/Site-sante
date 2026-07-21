from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accueil", "0003_articleveille_categories_articleveille_importance_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="veillequotidienne",
            name="resume_manuel",
            field=models.TextField(blank=True, verbose_name="Résumé manuel"),
        ),
        migrations.AddField(
            model_name="veillequotidienne",
            name="resume_manuel_publie",
            field=models.BooleanField(default=False, verbose_name="Publier le résumé manuel"),
        ),
        migrations.AlterField(
            model_name="veillequotidienne",
            name="resume",
            field=models.TextField(blank=True, verbose_name="Résumé automatique"),
        ),
        migrations.AddField(
            model_name="articleveille",
            name="titre_traduit_auto",
            field=models.TextField(blank=True, verbose_name="Titre traduit automatiquement"),
        ),
        migrations.AddField(
            model_name="articleveille",
            name="resume_traduit_auto",
            field=models.TextField(blank=True, verbose_name="Résumé traduit automatiquement"),
        ),
        migrations.AddField(
            model_name="articleveille",
            name="titre_traduit_manuel",
            field=models.TextField(blank=True, verbose_name="Titre traduit manuellement"),
        ),
        migrations.AddField(
            model_name="articleveille",
            name="resume_traduit_manuel",
            field=models.TextField(blank=True, verbose_name="Résumé traduit manuellement"),
        ),
        migrations.AddField(
            model_name="articleveille",
            name="traduction_manuelle_publiee",
            field=models.BooleanField(default=False, verbose_name="Publier la traduction manuelle"),
        ),
    ]
