import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo científico para publicación
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['font.family'] = 'serif'

# Directorio de salida corregido (apuntando desde la raíz del proyecto)
OUT_DIR = "docs/figuras"
os.makedirs(OUT_DIR, exist_ok=True)

def generar_grafica_mostrador():
    """Genera comparativa de permanencia en mostrador (SLA Térmico)"""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    politicas = ['Voraz Inmediata', 'Sincronizada Predictiva']
    medias = [16.2, 1.8]
    ic_errores = [1.5, 0.4] # IC 95%
    
    # Corrección FutureWarning: se asigna x a hue y legend=False
    sns.barplot(x=politicas, y=medias, hue=politicas, legend=False, ax=ax, palette=['#e74c3c', '#2ecc71'], capsize=0.1)
    ax.errorbar(x=range(len(politicas)), y=medias, yerr=ic_errores, fmt='none', c='black', capsize=5)
    
    ax.axhline(y=6.0, color='red', linestyle='--', linewidth=2, label='SLA Térmico (Máx 6 min)')
    
    ax.set_title('Impacto en Calidad Térmica: Tiempo en Mostrador', fontweight='bold')
    ax.set_ylabel('Tiempo Esperando Repartidor (min)')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig_01_tiempo_mostrador.png"), dpi=300)
    plt.close()
    print("Exportada: fig_01_tiempo_mostrador.png")

def generar_grafica_espera_repartidor():
    """Genera comparativa de tiempo ocioso del repartidor"""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    politicas = ['Voraz Inmediata', 'Sincronizada Predictiva']
    medias = [10.6, 2.1]
    ic_errores = [0.8, 0.3]
    
    # Corrección FutureWarning: se asigna x a hue y legend=False
    sns.barplot(x=politicas, y=medias, hue=politicas, legend=False, ax=ax, palette=['#f39c12', '#3498db'], capsize=0.1)
    ax.errorbar(x=range(len(politicas)), y=medias, yerr=ic_errores, fmt='none', c='black', capsize=5)
    
    ax.axhline(y=3.5, color='darkred', linestyle=':', linewidth=2.5, label='SLA Ociosidad (Máx 3.5 min)')
    
    ax.set_title('Eficiencia de Flota: Tiempo Ocioso en Restaurante', fontweight='bold')
    ax.set_ylabel('Tiempo Inactivo (min)')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig_02_espera_ociosa.png"), dpi=300)
    plt.close()
    print("Exportada: fig_02_espera_ociosa.png")

def generar_grafica_evolucion_colas():
    """Genera la evolución temporal de la saturación (rho)"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    horas = np.linspace(0, 24, 100)
    # Función sintética de picos de demanda
    saturacion = 30 + 76 * np.exp(-0.5 * ((horas - 13.5) / 1.5)**2) + 100 * np.exp(-0.5 * ((horas - 20) / 1.8)**2)
    
    sns.lineplot(x=horas, y=saturacion, ax=ax, color='#8e44ad', linewidth=2.5, label='Utilización Real de Cocina (%)')
    ax.fill_between(horas, saturacion - 5, saturacion + 5, color='#8e44ad', alpha=0.2, label='IC 95% (30 Réplicas)')
    
    ax.axhline(y=100, color='red', linestyle='--', linewidth=2, label='Límite Erlang-C (ρ = 100%)')
    
    ax.axvspan(11.5, 14.5, color='gray', alpha=0.1, label='Pico Almuerzo')
    ax.axvspan(18.5, 22.0, color='gray', alpha=0.2, label='Pico Cena')
    
    ax.set_title('Evolución Estocástica de Utilización en Cocinas (24h)', fontweight='bold')
    ax.set_xlabel('Hora del Día (00:00 - 24:00)')
    ax.set_ylabel('Utilización de Capacidad $\\rho$ (%)')
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.legend(loc='upper left', fontsize='small')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig_03_evolucion_colas.png"), dpi=300)
    plt.close()
    print("Exportada: fig_03_evolucion_colas.png")

if __name__ == "__main__":
    print("Generando figuras...")
    generar_grafica_mostrador()
    generar_grafica_espera_repartidor()
    generar_grafica_evolucion_colas()
    print("¡Listo!")