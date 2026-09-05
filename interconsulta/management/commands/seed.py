from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from interconsulta.models import EstablecimientoSalud, Paciente, Profesional


class Command(BaseCommand):
    help = (
        'Crea la base minima para operar la app recien desplegada: un '
        'superusuario, establecimientos, un profesional medico general, un '
        'especialista y pacientes de ejemplo. NO crea CasoTriaje ni '
        'ColaInterconsulta (eso se genera usando la app). Seguro de correr '
        'mas de una vez: no duplica nada ni pisa contrasenas existentes.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self._crear_admin()
        posta, hospital = self._crear_establecimientos()
        self._crear_profesional(
            'jack', 'jack123', Profesional.Rol.MEDICO_GENERAL, posta, 'Medicina general'
        )
        self._crear_profesional(
            'santiago', 'santiago123', Profesional.Rol.ESPECIALISTA, hospital, 'Dermatologia'
        )
        self._crear_pacientes()
        self.stdout.write(self.style.SUCCESS('Datos iniciales listos.'))

    def _crear_admin(self):
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write('Superusuario "admin" creado.')
        else:
            self.stdout.write('Superusuario "admin" ya existia, no se toco.')

    def _crear_establecimientos(self):
        posta, _ = EstablecimientoSalud.objects.get_or_create(
            nombre='Posta de Salud San Juan',
            defaults=dict(
                codigo_renaes='0001234',
                nivel='I-2',
                departamento='Cusco',
                provincia='Canchis',
                distrito='Sicuani',
                tiene_conectividad_estable=False,
            ),
        )
        hospital, _ = EstablecimientoSalud.objects.get_or_create(
            nombre='Hospital Regional del Cusco',
            defaults=dict(
                codigo_renaes='0005678',
                nivel='I-4',
                departamento='Cusco',
                provincia='Cusco',
                distrito='Cusco',
                tiene_conectividad_estable=True,
            ),
        )
        self.stdout.write('Establecimientos listos.')
        return posta, hospital

    def _crear_profesional(self, username, password, rol, establecimiento, especialidad):
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
            user.save()
        # el signal crear_perfil_profesional ya le creo un Profesional(MEDICO_GENERAL)
        # apenas se guardo el User; aca solo lo ajustamos al rol que corresponde.
        profesional = user.profesional
        profesional.rol = rol
        profesional.establecimiento = establecimiento
        profesional.especialidad = especialidad
        profesional.save()
        self.stdout.write(f'Profesional "{username}" listo ({rol}).')

    def _crear_pacientes(self):
        pacientes = [
            dict(
                tipo_documento='DNI', numero_documento='45678912',
                nombres='Rosa Elena', apellidos='Quispe Mamani', edad=58, sexo='F',
            ),
            dict(
                tipo_documento='DNI', numero_documento='71234567',
                nombres='Carlos Alberto', apellidos='Fernandez Rojas', edad=34, sexo='M',
            ),
            dict(
                tipo_documento='DNI', numero_documento='62345178',
                nombres='Maria Fernanda', apellidos='Huayta Condori', edad=45, sexo='F',
            ),
            dict(
                tipo_documento='CE', numero_documento='CE1234567',
                nombres='Juan Pablo', apellidos='Rodriguez Silva', edad=29, sexo='M',
            ),
        ]
        for datos in pacientes:
            Paciente.objects.get_or_create(
                tipo_documento=datos['tipo_documento'],
                numero_documento=datos['numero_documento'],
                defaults=datos,
            )
        self.stdout.write(f'{len(pacientes)} paciente(s) de ejemplo listos.')
