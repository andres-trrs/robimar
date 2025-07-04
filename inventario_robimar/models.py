from django.db import models
from datetime import timedelta
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class Cliente(models.Model):
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(
        max_length=9,
        validators=[
            RegexValidator(
                regex=r'^\d{9}$',
                message="El número de teléfono debe contener exactamente 9 dígitos numéricos."
            )
        ]
    )
    email = models.EmailField(
        blank=False,
        unique=True,
        error_messages={
            'invalid': "Debe ingresar un correo válido en el formato ejemplo@dominio.com"
        }
    )

    def save(self, *args, **kwargs):
        if self.rut.isdigit():
            self.rut = f"{self.rut}-{self.calcular_dv(self.rut)}"
        super().save(*args, **kwargs)

    @staticmethod
    def calcular_dv(rut_base):
        reversed_digits = map(int, reversed(str(rut_base)))
        factors = [2, 3, 4, 5, 6, 7] * 2
        s = sum(d * f for d, f in zip(reversed_digits, factors))
        res = 11 - (s % 11)
        if res == 11:
            return '0'
        elif res == 10:
            return 'K'
        else:
            return str(res)

    def __str__(self):
        return self.nombre


class Material(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    valor_arriendo = models.DecimalField(max_digits=10, decimal_places=2)  # por día
    stock_total = models.PositiveIntegerField()
    stock_disponible = models.PositiveIntegerField()
    habilitado = models.BooleanField(default=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.stock_disponible}/{self.stock_total})"


class Arriendo(models.Model):
    ESTADOS = [
        ('activo', 'Activo'),
        ('devuelto', 'Devuelto'),
        ('cancelado', 'Cancelado'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_arriendo = models.DateField()
    fecha_devolucion = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='activo')

    def save(self, *args, **kwargs):
        if self.pk:
            estado_anterior = Arriendo.objects.get(pk=self.pk).estado
            if estado_anterior == 'activo' and self.estado == 'devuelto':
                self.devolver()
            elif estado_anterior == 'activo' and self.estado == 'cancelado':
                self.cancelar()
        super().save(*args, **kwargs)

    def dias_arriendo(self):
        dias = (self.fecha_devolucion - self.fecha_arriendo).days
        return dias if dias > 0 else 1

    def devolver(self):
        for detalle in self.detalles.all():
            material = detalle.material
            material.stock_disponible += detalle.cantidad
            material.save()
        return "Materiales devueltos correctamente."

    def cancelar(self):
        for detalle in self.detalles.all():
            material = detalle.material
            material.stock_disponible += detalle.cantidad
            material.save()
        return "Arriendo cancelado y stock restituido."

    def valor_total(self):
        return sum(detalle.valor_total() for detalle in self.detalles.all())

    def __str__(self):
        return f"Arriendo #{self.id} - {self.cliente.nombre}"


class ArriendoDetalle(models.Model):
    arriendo = models.ForeignKey(Arriendo, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    def dias_arriendo(self):
        return self.arriendo.dias_arriendo()

    def valor_unitario(self):
        return self.material.valor_arriendo

    def valor_total(self):
        return self.valor_unitario() * self.cantidad * self.dias_arriendo()

    def __str__(self):
        return f"{self.material.nombre} x{self.cantidad} (#{self.arriendo.id})"


@receiver(post_save, sender=ArriendoDetalle)
def descontar_stock_al_crear(sender, instance, created, **kwargs):
    if created and instance.arriendo.estado == 'activo':
        material = instance.material
        if instance.cantidad > material.stock_disponible:
            raise ValueError(f"No hay suficiente stock disponible para {material.nombre}.")
        material.stock_disponible -= instance.cantidad
        material.save()


@receiver(pre_delete, sender=ArriendoDetalle)
def devolver_stock_al_eliminar(sender, instance, **kwargs):
    if instance.arriendo.estado == 'activo':
        material = instance.material
        material.stock_disponible += instance.cantidad
        material.save()