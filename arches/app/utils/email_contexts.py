from arches.app.models.system_settings import settings
import logging

def return_email_context(greeting=None,export_id_link=None,button_text=None,closing_text=None,email=None,export_name=None,email_export_link=None,user=None):
    try:
        email_context =  dict(
            greeting = greeting,
            link = export_id_link,
            button_text= button_text,
            closing= closing_text,
            email=email,
            name=export_name,
            email_link=email_export_link,
        )

        if user != None:
            username = user.first_name + " " + user.last_name
            email_context["username"] = username

        if settings.EXTRA_EMAIL_CONTEXT != {}:
            for k,v in settings.EXTRA_EMAIL_CONTEXT.items():
                email_context[k] = v

        return email_context

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error('Setting email context failed',str(e))

        return {}