import re

from airgun.entities.base import BaseEntity
from airgun.navigation import NavigateStep
from airgun.navigation import navigator
from airgun.views.errata import ErrataDetailsView
from airgun.views.errata import ErrataInstallationConfirmationView
from airgun.views.errata import ErrataTaskDetailsView
from airgun.views.errata import ErratumView
from airgun.views.job_invocation import JobInvocationStatusView


class ErrataEntity(BaseEntity):
    endpoint_path = '/errata'

    def search(self, value, applicable=True, installable=False, repo=None):
        """Search for specific errata.

        :param str value: search query to type into search field.
        :param bool applicable: filter by only applicable errata
        :param bool installable: filter by only installable errata
        :param str optional repo: filter by repository name
        :return: list of dicts representing table rows
        :rtype: list
        """
        view = self.navigate_to(self, 'All')
        return view.search(value, applicable=applicable, installable=installable, repo=repo)

    def read(
        self,
        entity_name,
        applicable=False,
        installable=False,
        repo=None,
        environment=None,
        widget_names=None,
    ):
        """Read errata details.

        :param str entity_name: errata id or title
        :param bool applicable: filter by only applicable errata
        :param bool installable: filter by only installable errata
        :param str optional repo: filter by repository name
        :param str optional environment: filter applicable hosts by environment
            name
        :return: dict representing tabs, with nested dicts representing fields
            and values
        :rtype: dict
        """
        view = self.navigate_to(
            self,
            'Details',
            entity_name=entity_name,
            applicable=applicable,
            installable=installable,
            repo=repo,
        )
        if environment:
            view.content_hosts.environment_filter.fill(environment)
        return view.read(widget_names=widget_names)

    def install(self, entity_name, host_name, installed_via=None):
        """Install errata on content host.

        The installation method is not set here, but the path changes according to the method used.
        For katello-agent, the Content Hosts' Task tab displays the progress. If REX is used,
        the Job Invocation view displays the progress. In 6.10, REX became the default method.

        :param str entity_name: errata id or title
        :param str host_name: content host name to apply errata on
        :param installed_via: what installation method was used
        """
        view = self.navigate_to(
            self,
            'Details',
            entity_name=entity_name,
            applicable=False,
            installable=False,
            repo=None,
        )
        view.content_hosts.search(host_name)
        view.content_hosts.table.row(name=host_name)[0].fill(True)
        view.content_hosts.apply.click()
        view = ErrataInstallationConfirmationView(view.browser)
        view.confirm.click()
        if installed_via == 'katello':
            view = ErrataTaskDetailsView(view.browser)
            view.progressbar.wait_for_result()
        else:
            view = JobInvocationStatusView(view.browser)
            view.wait_for_result()
        return view.read()

    def search_content_hosts(self, entity_name, value, environment=None):
        """Search errata applicability for content hosts.

        :param str entity_name: errata id or title
        :param str value: search query to type into search field.
        :param str optional environment: filter applicable hosts by environment name
        """
        view = self.navigate_to(
            self,
            'Details',
            entity_name=entity_name,
            applicable=False,
            installable=False,
            repo=None,
        )
        return view.content_hosts.search(value, environment=environment)


@navigator.register(ErrataEntity, 'All')
class ShowAllErratum(NavigateStep):
    """Navigate to All Erratum screen."""

    VIEW = ErratumView

    def step(self, *args, **kwargs):
        self.view.menu.select('Content', 'Errata')


@navigator.register(ErrataEntity, 'Details')
class ErrataDetails(NavigateStep):
    """Navigate to Errata details page.

    Args:
        entity_name: id or title of errata

    Optional Args:
        applicable: whether to filter errata by only applicable ones
        installable: whether to filter errata by only installable ones
        repo: name of repository to filter errata by
    """

    VIEW = ErrataDetailsView

    def prerequisite(self, *args, **kwargs):
        return self.navigate_to(self.obj, 'All')

    def step(self, *args, **kwargs):
        entity_name = kwargs.get('entity_name')
        applicable = kwargs.get('applicable')
        installable = kwargs.get('installable')
        repo = kwargs.get('repo')
        self.parent.search(entity_name, applicable=applicable, installable=installable, repo=repo)
        row_filter = {'title': entity_name}
        if re.search(r'\w{3,4}[:-]\d{4}[-:]\d{4}', entity_name):
            row_filter = {'errata_id': entity_name}
        self.parent.table.row(**row_filter)['Errata ID'].widget.click()
