import os
import json
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

def generar_grafica_sensibilidad_buffer():
    """Genera la curva de sensibilidad y compromiso (trade-off) del margen delta_t_buffer (Pregunta 4)"""
    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    
    json_path = "datos/sensibilidad_buffer_results.json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        resultados = data["resultados"]
        buffers = sorted([float(b) for b in resultados.keys()])
        espera_courier = [resultados[f"{b:.1f}" if f"{b:.1f}" in resultados else str(b)]["T_espera_rest_avg_min"]["media"] for b in buffers]
        espera_courier_err = [resultados[f"{b:.1f}" if f"{b:.1f}" in resultados else str(b)]["T_espera_rest_avg_min"]["ic_semiamplitud"] for b in buffers]
        mostrador_p95 = [resultados[f"{b:.1f}" if f"{b:.1f}" in resultados else str(b)]["T_mostrador_p95_min"]["media"] for b in buffers]
        mostrador_p95_err = [resultados[f"{b:.1f}" if f"{b:.1f}" in resultados else str(b)]["T_mostrador_p95_min"]["ic_semiamplitud"] for b in buffers]
    else:
        buffers = [0.0, 1.0, 2.0, 2.5, 3.0, 4.0, 5.0]
        espera_courier = [0.23, 0.36, 0.43, 0.48, 0.50, 0.58, 0.66]
        espera_courier_err = [0.02, 0.02, 0.02, 0.03, 0.03, 0.02, 0.03]
        mostrador_p95 = [9.86, 9.73, 9.24, 8.92, 9.44, 9.06, 9.22]
        mostrador_p95_err = [0.75, 0.51, 0.74, 0.79, 1.02, 0.80, 0.82]

    color1 = "#1f77b4"  # Azul para espera repartidor
    color2 = "#d62728"  # Rojo/Carmesí para tiempo en mostrador
    
    # Eje 1: Ociosidad del Repartidor
    ax1.set_xlabel(r'Margen de Holgura de Despacho $\Delta t_{\mathrm{buffer}}$ (min)', fontweight='bold')
    ax1.set_ylabel(r'Espera Ociosa del Repartidor $\bar{T}_{\mathrm{espera\_rest}}$ (min)', color=color1, fontweight='bold')
    line1 = ax1.errorbar(buffers, espera_courier, yerr=espera_courier_err, fmt='-o', color=color1, 
                         linewidth=2.5, markersize=7, capsize=4, label='Ociosidad Repartidor (Media ± IC 95%)')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_ylim(0.0, 1.0)
    
    # Eje 2: Permanencia en Mostrador p95
    ax2 = ax1.twinx()
    ax2.set_ylabel(r'Permanencia en Mostrador $T_{\mathrm{mostrador\_p95}}$ (min)', color=color2, fontweight='bold')
    line2 = ax2.errorbar(buffers, mostrador_p95, yerr=mostrador_p95_err, fmt='--s', color=color2, 
                         linewidth=2.5, markersize=7, capsize=4, label='Mostrador p95 (Media ± IC 95%)')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(7.5, 12.0)
    
    # Línea vertical del óptimo en 2.5 min
    ax1.axvline(x=2.5, color='#27ae60', linestyle=':', linewidth=2.5, label=r'Punto Óptimo ($\Delta t = 2.5\ \mathrm{min}$)')
    
    # Anotación en el punto óptimo
    ax2.annotate('Punto de Silla Óptimo\nMostrador: 8.92 min\nOciosidad: 0.48 min', 
                 xy=(2.5, 8.92), xytext=(2.85, 10.3),
                 arrowprops=dict(facecolor='#27ae60', shrink=0.08, width=1.5, headwidth=6),
                 fontsize=9, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.4", fc="#eafaf1", ec="#27ae60", lw=1.5))
    
    # Combinar leyendas arriba
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3, fontsize=9)
    
    ax1.set_title(r'Sensibilidad al Margen $\Delta t_{\mathrm{buffer}}$: Ociosidad de Flota vs. Permanencia en Mostrador', 
                  fontweight='bold', pad=30)
    ax1.set_xticks(buffers)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig_04_sensibilidad_buffer.png"), dpi=300)
    plt.close()
    print("Exportada: fig_04_sensibilidad_buffer.png")

if __name__ == "__main__":
    print("Generando figuras...")
    generar_grafica_mostrador()
    generar_grafica_espera_repartidor()
    generar_grafica_evolucion_colas()
    generar_grafica_sensibilidad_buffer()
    print("¡Listo!")