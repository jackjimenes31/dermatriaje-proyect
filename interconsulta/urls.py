from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('establecimientos', views.EstablecimientoSaludViewSet)
router.register('profesionales', views.ProfesionalViewSet)
router.register('pacientes', views.PacienteViewSet)
router.register('casos-triaje', views.CasoTriajeViewSet)
router.register('cola-interconsulta', views.ColaInterconsultaViewSet)

urlpatterns = router.urls
