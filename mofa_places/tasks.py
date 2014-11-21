import logging
import bz2
import zipfile
import requests

from celery import chain
from xml.sax import make_parser

from moxie import create_app
from moxie.worker import celery
from moxie.core.tasks import get_resource
from moxie.core.search import searcher
from moxie.core.kv import kv_store
from mofa_places.importers.sbb import SbbStationImporter

logger = logging.getLogger(__name__)
BLUEPRINT_NAME = 'places'


@celery.task
def import_all(force_update_all=False):
    app = create_app()
    with app.blueprint_context(BLUEPRINT_NAME):

        solr_server = app.config['PLACES_SOLR_SERVER']

        staging_core = app.config['PLACES_SOLR_CORE_STAGING']
        production_core = app.config['PLACES_SOLR_CORE_PRODUCTION']

        staging_core_url = '{server}/{core}/update'.format(server=solr_server, core=staging_core)

        delete_response = requests.post(staging_core_url, '<delete><query>*:*</query></delete>', headers={'Content-type': 'text/xml'})
        commit_response = requests.post(staging_core_url, '<commit/>', headers={'Content-type': 'text/xml'})

        if delete_response.ok and commit_response.ok:
            logger.info("Deleted all documents from staging, launching importers")
            # Using a chain (seq) so tasks execute in order
            res = chain(#import_osm.s(force_update=force_update_all),
                        import_sbb_stations.s(force_update=force_update_all),
                        #import_swiss_library_data.s(force_update=force_update_all)
            )()
            res.get() # Get will block until all tasks complete
            if all([r[1] for r in res.collect()]):    # if all results are True
                swap_response = requests.get("{server}/admin/cores?action=SWAP&core={new}&other={old}".format(server=solr_server,
                                                                                                              new=production_core,
                                                                                                              old=staging_core))
                if swap_response.ok:
                    logger.info("Cores swapped")
                else:
                    logger.warning("Error when swapping core {response}".format(response=swap_response.status_code))
            else:
                logger.warning("Didn't swap cores because some errors happened")
        else:
            logger.warning("Staging core not deleted correctly, aborting")


@celery.task
def import_sbb_stations(previous_result=None, url=None, force_update=False):
    if previous_result not in [None, True]:
        return False
    app = create_app()
    with app.blueprint_context(BLUEPRINT_NAME):
        url = url or app.config['SBB_IMPORT_URL']
        db = get_resource(url, force_update)
        if db:
            sbb_importer = SbbStationImporter(searcher, 10, db, ['340'], 'identifiers')
            sbb_importer.run()
        else:
            logger.info("SBB stations haven't been imported - resource not loaded")
            return False
    return True


@celery.task
def import_swiss_library_data(previous_result=None, url=None, force_update=False):
    if previous_result not in [None, True]:
        return False
    app = create_app()
    with app.blueprint_context(BLUEPRINT_NAME):
        return True   # XXX add some code
        url = url or app.config['SWISS_LIBRARY_IMPORT_URL']
        oxpoints = get_resource(url, force_update, media_type=RDF_MEDIA_TYPE)
        if oxpoints:
            logger.info("OxPoints Downloaded - Stored here: %s" % oxpoints)
            oxpoints = open(oxpoints)
            importer = OxpointsDescendantsImporter(kv_store, oxpoints, Org.subOrganizationOf,
                                                   rdf_media_type=RDF_MEDIA_TYPE)
            importer.import_data()
        else:
            logger.info("OxPoints descendants hasn't been imported - resource not loaded")
            return False
    return True
