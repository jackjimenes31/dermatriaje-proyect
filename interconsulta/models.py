import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class EstablecimientoSalud(models.Model):
    class Nivel(models.TextChoices):
        I_1 = 'I-1', 'I-1'
        I_2 = 'I-2', 'I-2'
        I_3 = 'I-3', 'I-3'
        I_4 = 'I-4', 'I-4'

    nombre = models.CharField(max_length=200)
    codigo_renaes = models.CharField(max_length=20, blank=True)
    nivel = models.CharField(max_length=3, choices=Nivel.choices)
    departamento = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)
    distrito = models.CharField(max_length=100)
    tiene_conectividad_estable = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['departamento', 'provincia', 'distrito', 'nombre']

    def __str__(self):
        return f'{self.nombre} ({self.nivel})'


class Profesional(models.Model):
    class Rol(models.TextChoices):
        MEDICO_GENERAL = 'MEDICO_GENERAL', 'Médico general'
        SERUMISTA = 'SERUMISTA', 'Serumista'
        ESPECIALISTA = 'ESPECIALISTA', 'Especialista'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profesional'
    )
    rol = models.CharField(max_length=20, choices=Rol.choices)
    establecimiento = models.ForeignKey(
        EstablecimientoSalud,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profesionales',
    )
    especialidad = models.CharField(max_length=100, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_rol_display()})'


class Paciente(models.Model):
    class TipoDocumento(models.TextChoices):
        DNI = 'DNI', 'DNI'
        CE = 'CE', 'Carné de Extranjería'

    class Sexo(models.TextChoices):
        M = 'M', 'Masculino'
        F = 'F', 'Femenino'
        OTRO = 'OTRO', 'Otro'

    tipo_documento = models.CharField(
        max_length=3, choices=TipoDocumento.choices, default=TipoDocumento.DNI
    )
    numero_documento = models.CharField(max_length=15)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    edad = models.PositiveSmallIntegerField()
    sexo = models.CharField(max_length=4, choices=Sexo.choices)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_documento', 'numero_documento'],
                name='unique_documento_paciente',
            )
        ]

    def __str__(self):
        return f'{self.nombres} {self.apellidos} ({self.tipo_documento} {self.numero_documento})'

    def clean(self):
        if self.tipo_documento == self.TipoDocumento.DNI and not re.fullmatch(
            r'\d{8}', self.numero_documento
        ):
            raise ValidationError({'numero_documento': 'El DNI debe tener exactamente 8 dígitos.'})
        if self.tipo_documento == self.TipoDocumento.CE and not re.fullmatch(
            r'[A-Za-z0-9]{8,12}', self.numero_documento
        ):
            raise ValidationError(
                {'numero_documento': 'El Carné de Extranjería debe tener entre 8 y 12 caracteres alfanuméricos.'}
            )


class CasoTriaje(models.Model):
    class TipoLesion(models.TextChoices):
        """ salida del Skin-Lesion-Classifier """

        AKIEC = 'akiec', 'Queratosis actínica / enfermedad de Bowen'
        BCC = 'bcc', 'Carcinoma basocelular'
        BKL = 'bkl', 'Lesión queratósica benigna'
        DF = 'df', 'Dermatofibroma'
        MEL = 'mel', 'Melanoma'
        NV = 'nv', 'Nevo melanocítico'
        VASC = 'vasc', 'Lesión vascular'

    class ClasificacionRiesgo(models.TextChoices):
        BAJO = 'BAJO', 'Bajo riesgo'
        MEDIO = 'MEDIO', 'Riesgo medio'
        ALTO = 'ALTO', 'Alto riesgo'

    class Estado(models.TextChoices):
        REGISTRADO = 'REGISTRADO', 'Registrado'
        RESUELTO_LOCAL = 'RESUELTO_LOCAL', 'Resuelto en el mismo nivel'
        EN_COLA_INTERCONSULTA = 'EN_COLA_INTERCONSULTA', 'En cola de interconsulta'

    # Mapeo entre el tipo de lesion y nivel de riesgo
    RIESGO_POR_TIPO_LESION = {
        TipoLesion.MEL: ClasificacionRiesgo.ALTO,
        TipoLesion.BCC: ClasificacionRiesgo.ALTO,
        TipoLesion.AKIEC: ClasificacionRiesgo.ALTO,
        TipoLesion.BKL: ClasificacionRiesgo.MEDIO,
        TipoLesion.NV: ClasificacionRiesgo.BAJO,
        TipoLesion.DF: ClasificacionRiesgo.BAJO,
        TipoLesion.VASC: ClasificacionRiesgo.BAJO,
    }

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name='casos')
    profesional_creador = models.ForeignKey(
        Profesional, on_delete=models.PROTECT, related_name='casos_creados'
    )
    establecimiento = models.ForeignKey(
        EstablecimientoSalud, on_delete=models.PROTECT, related_name='casos'
    )
    fecha_evaluacion = models.DateTimeField(auto_now_add=True)
    tipo_lesion_predicho = models.CharField(max_length=5, choices=TipoLesion.choices)
    confianza_modelo = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    probabilidades_top3 = models.JSONField(
        blank=True,
        null=True,
        help_text='Top-3 predicciones del modelo, ej. [{"tipo": "mel", "confianza": 0.62}, ...].',
    )
    modelo_version = models.CharField(
        max_length=50, blank=True, default='skin-lesion-classifier-mobilenet-ham10000-tfjs'
    )
    clasificacion_riesgo = models.CharField(max_length=5, choices=ClasificacionRiesgo.choices)
    estado = models.CharField(
        max_length=25, choices=Estado.choices, default=Estado.REGISTRADO
    )
    profesional_resuelve = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='casos_resueltos',
        help_text=(
            'Profesional que cerró el caso'
        ),
    )
    fecha_resolucion = models.DateTimeField(
        null=True, blank=True, help_text='Fecha del cierre del caso.'
    )
    notas_clinicas = models.TextField(blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_evaluacion']

    def __str__(self):
        return f'Caso #{self.pk} - {self.paciente} ({self.tipo_lesion_predicho})'

    @property
    def riesgo_sugerido(self):
        return self.RIESGO_POR_TIPO_LESION.get(self.tipo_lesion_predicho)


class ColaInterconsulta(models.Model):
    class Prioridad(models.TextChoices):
        URGENTE = 'URGENTE', 'Urgente'
        ALTA = 'ALTA', 'Alta'
        MEDIA = 'MEDIA', 'Media'

    class Estado(models.TextChoices):
        EN_ESPERA = 'EN_ESPERA', 'En espera'
        EN_ATENCION = 'EN_ATENCION', 'En atención'
        RESUELTO = 'RESUELTO', 'Resuelto'
        CANCELADO = 'CANCELADO', 'Cancelado'

    caso = models.OneToOneField(
        CasoTriaje, on_delete=models.CASCADE, related_name='cola_interconsulta'
    )
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices)
    especialista_asignado = models.ForeignKey(
        Profesional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='casos_asignados',
        limit_choices_to={'rol': Profesional.Rol.ESPECIALISTA},
    )
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.EN_ESPERA
    )
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_atencion = models.DateTimeField(null=True, blank=True)
    observaciones_especialista = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_ingreso']
        verbose_name_plural = 'Colas de interconsulta'

    def __str__(self):
        return f'Interconsulta caso #{self.caso_id} ({self.estado})'
