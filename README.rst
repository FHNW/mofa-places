==========================
moxie-sbb
==========================

TBD [Write some description, usage, etc. documentation here]

Moxie blueprint: ::

  services:
      sbb:
          <XXX>Service:
              providers:
                  moxie_sbb.providers.<XXX>:
                      url: 'http://fhnw.sv-group.ch/de.html'
          KVService:
              backend_uri: 'redis://localhost:6379/0'


Celery configuration: ::

  # List of modules to import when celery starts.
  CELERY_IMPORTS = (..., "moxie_sbb.tasks")


Import data ::

  >>> from moxie_food.tasks import import_sbb
  >>> import_sbb.delay()
