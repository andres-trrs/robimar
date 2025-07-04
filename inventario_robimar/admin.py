from django.contrib import admin
from .models import Cliente, Material, Arriendo, ArriendoDetalle
from django.contrib.admin import TabularInline


@admin.action(description="Marcar como DEVUELTO y devolver stock")
def marcar_como_devuelto(modeladmin, request, queryset):
    for arriendo in queryset:
        resultado = arriendo.devolver()
        modeladmin.message_user(request, f"Arriendo #{arriendo.id}: {resultado}")


@admin.action(description="CANCELAR arriendo y devolver stock")
def cancelar_arriendo(modeladmin, request, queryset):
    for arriendo in queryset:
        resultado = arriendo.cancelar()
        modeladmin.message_user(request, f"Arriendo #{arriendo.id}: {resultado}")


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'stock_disponible', 'stock_total', 'valor_arriendo', 'habilitado')
    list_filter = ('habilitado',)
    search_fields = ('nombre',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'telefono', 'email')
    search_fields = ('nombre', 'rut')

class ArriendoDetalleInline(admin.TabularInline):
    model = ArriendoDetalle
    extra = 1  
    autocomplete_fields = ['material']  


@admin.register(Arriendo)
class ArriendoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha_arriendo', 'fecha_devolucion', 'estado', 'mostrar_total')
    list_filter = ('estado', 'fecha_arriendo')
    autocomplete_fields = ['cliente']
    actions = [marcar_como_devuelto, cancelar_arriendo]
    search_fields = ('cliente__nombre',)
    inlines = [ArriendoDetalleInline] 

    def mostrar_total(self, obj):
        return f"${obj.valor_total():,.0f}"
    mostrar_total.short_description = "Valor total"


@admin.register(ArriendoDetalle)
class ArriendoDetalleAdmin(admin.ModelAdmin):
    list_display = ('arriendo', 'material', 'cantidad', 'mostrar_valor_unitario', 'mostrar_valor_total')
    list_filter = ('material',)
    search_fields = ('arriendo__id', 'material__nombre')

    def mostrar_valor_unitario(self, obj):
        return f"${obj.valor_unitario():,.0f}"

    def mostrar_valor_total(self, obj):
        return f"${obj.valor_total():,.0f}"

    mostrar_valor_unitario.short_description = "Valor unitario"
    mostrar_valor_total.short_description = "Valor total"
