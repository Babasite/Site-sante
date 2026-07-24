from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def contact(request):
    """Affiche le formulaire de contact et transmet le message sans exposer l'adresse destinataire."""
    form_data = {"nom": "", "email": "", "sujet": "", "message": ""}

    if request.method == "POST":
        form_data = {
            "nom": request.POST.get("nom", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "sujet": request.POST.get("sujet", "").strip(),
            "message": request.POST.get("message", "").strip(),
        }

        # Champ invisible anti-robot : un vrai visiteur le laisse vide.
        if request.POST.get("website", "").strip():
            messages.success(
                request,
                "Votre message a bien été envoyé. Nous vous répondrons dans les meilleurs délais.",
            )
            return redirect("contact")

        if not all(form_data.values()):
            messages.error(request, "Merci de remplir tous les champs du formulaire.")
            return render(request, "accueil/contact.html", {"form_data": form_data})

        recipient = getattr(settings, "CONTACT_EMAIL", "").strip()
        if not recipient:
            messages.error(
                request,
                "L'envoi de messages n'est pas encore configuré. Merci de réessayer ultérieurement.",
            )
            return render(request, "accueil/contact.html", {"form_data": form_data})

        safe_name = strip_tags(form_data["nom"])[:120]
        safe_subject = strip_tags(form_data["sujet"]).replace("\r", " ").replace("\n", " ")[:160]
        reply_email = form_data["email"].replace("\r", "").replace("\n", "")[:254]
        safe_message = strip_tags(form_data["message"])[:10000]

        body = (
            "Nouveau message depuis Santé Prévention Terrain\n\n"
            f"Nom : {safe_name}\n"
            f"Adresse de réponse : {reply_email}\n"
            f"Sujet : {safe_subject}\n\n"
            "Message :\n"
            f"{safe_message}\n"
        )

        try:
            email = EmailMessage(
                subject=f"[Contact SPT] {safe_subject}",
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                to=[recipient],
                reply_to=[reply_email],
            )
            email.send(fail_silently=False)
        except Exception:
            messages.error(
                request,
                "Le message n'a pas pu être envoyé pour le moment. Merci de réessayer un peu plus tard.",
            )
            return render(request, "accueil/contact.html", {"form_data": form_data})

        messages.success(
            request,
            "Votre message a bien été envoyé. Nous vous répondrons dans les meilleurs délais.",
        )
        return redirect("contact")

    return render(request, "accueil/contact.html", {"form_data": form_data})
