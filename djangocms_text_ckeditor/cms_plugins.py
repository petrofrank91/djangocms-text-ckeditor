from django.forms.fields import CharField
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from cms import __version__ as cms_version
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from cms.utils.urlutils import admin_reverse

from .settings import TEXT_CKEDITOR_CONFIGURATION
from .widgets import TextEditorWidget
from .models import Text
from .utils import plugin_tags_to_user_html
from .forms import TextForm


class TextPlugin(CMSPluginBase):
    model = Text
    name = _("Text")
    form = TextForm
    render_template = "cms/plugins/text.html"
    change_form_template = "cms/plugins/text_plugin_change_form.html"
    ckeditor_configuration = TEXT_CKEDITOR_CONFIGURATION


    def get_editor_widget(self, request, plugins, pk, placeholder, language):
        """
        Returns the Django form Widget to be used for
        the text area
        """
        return TextEditorWidget(installed_plugins=plugins, pk=pk,
                                placeholder=placeholder,
                                plugin_language=language,
                                configuration=self.ckeditor_configuration)

    def get_form_class(self, request, plugins, pk, placeholder, language):
        """
        Returns a subclass of Form to be used by this plugin
        """
        # We avoid mutating the Form declared above by subclassing
        class TextPluginForm(self.form):
            pass

        widget = self.get_editor_widget(request, plugins, pk, placeholder, language)
        TextPluginForm.declared_fields["body"] = CharField(
            widget=widget, required=False
        )
        return TextPluginForm

    def add_view(self, request, form_url='', extra_context=None):
        """
        This is a special case add view for the Text Plugin. Plugins should
        never have to create an instance on a GET request, but unfortunately
        the way the Text Plugin works (allowing child plugins on add), there is
        no way around here.

        If you're reading this code to learn how to write your own CMS Plugin,
        please read another plugin as you should not do what this plugin does.
        """
        if not hasattr(self, 'add_view_check_request'):
            # pre 3.1 compatiblity
            return super(TextPlugin, self).add_view(
                request, form_url, extra_context
            )
        result = self.add_view_check_request(request)
        if isinstance(result, HttpResponse):
            return result
        text = Text.objects.create(
            language=request.GET['plugin_language'],
            placeholder_id=request.GET['placeholder_id'],
            parent_id = request.GET.get(
                'plugin_parent', None
            ),
            plugin_type='TextPlugin',
            body=''
        )
        return HttpResponseRedirect(
            admin_reverse('cms_page_edit_plugin', args=(text.pk,))
        )

    def get_form(self, request, obj=None, **kwargs):
        plugins = plugin_pool.get_text_enabled_plugins(
            self.placeholder.slot,
            self.page
        )
        pk = self.cms_plugin_instance.pk
        form = self.get_form_class(request, plugins, pk, self.cms_plugin_instance.placeholder,
                                   self.cms_plugin_instance.language)
        kwargs['form'] = form  # override standard form
        return super(TextPlugin, self).get_form(request, obj, **kwargs)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """
        We override the change form template path
        to provide backwards compatibility with CMS 2.x
        """
        if cms_version.startswith('2'):
            context['change_form_template'] = "admin/cms/page/plugin_change_form.html"
        return super(TextPlugin, self).render_change_form(request, context, add, change, form_url, obj)

    def render(self, context, instance, placeholder):
        context.update({
            'body': plugin_tags_to_user_html(
                instance.body,
                context,
                placeholder
            ),
            'placeholder': placeholder,
            'object': instance
        })
        return context

    def save_model(self, request, obj, form, change):
        obj.clean_plugins()
        super(TextPlugin, self).save_model(request, obj, form, change)


plugin_pool.register_plugin(TextPlugin)
