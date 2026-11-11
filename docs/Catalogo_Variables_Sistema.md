# Diccionario de Variables del Sistema

Este documento explica de forma sencilla y directa todas las variables, parámetros y métricas que usamos en el simulador, en los modelos matemáticos y en la aplicación web.

---

## 1. Variables de Estado (¿Qué está pasando en el sistema en cada momento?)

| Nombre                                          |             Símbolo             | ¿Qué significa en palabras simples?                                                                     |
| :---------------------------------------------- | :------------------------------: | :-------------------------------------------------------------------------------------------------------- |
| **Pedidos en curso**                      |      $N_{\text{ped}}(t)$      | Cantidad de pedidos activos en ese instante (desde que el cliente pide hasta que se entregan o cancelan). |
| **Fila para la cocina**                   |     $Q_{\text{cocina}}(t)$     | Pedidos que están haciendo fila esperando a que se desocupe un fogón para empezar a cocinarse.          |
| **Fogones ocupados**                      |     $B_{\text{fogon}}(t)$     | Número de fogones que están cocinando comida en ese preciso momento.                                    |
| **Comida lista en mostrador**             |   $Q_{\text{mostrador}}(t)$   | Platos que ya están cocinados y están esperando en la barra a que llegue el repartidor a recogerlos.    |
| **Repartidores conectados**               |             $c(t)$             | Total de repartidores que tienen la app abierta y están trabajando en ese momento.                       |
| **Repartidores libres**                   |      $R_{\text{disp}}(t)$      | Repartidores que están desocupados esperando a que les caiga una orden.                                  |
| **Repartidores ocupados**                 |      $R_{\text{ocup}}(t)$      | Repartidores que ya aceptaron un pedido y van en camino al restaurante o hacia la casa del cliente.       |
| **Batería del celular**                  |       $\text{Bat}_i(t)$       | Porcentaje de carga que le queda al celular del repartidor en ese momento.                                |
| **Tiempo de turno trabajado**             |    $T_{\text{turno\_acum}}$    | Cuántos minutos lleva el repartidor conectado y trabajando desde que inició sesión en el día.         |
| **Cancelaciones por demora**              |   $N_{\text{canc\_cli}}(t)$   | Pedidos que el cliente canceló porque se cansó de esperar.                                              |
| **Cancelaciones por falta de repartidor** | $N_{\text{canc\_sin\_rep}}(t)$ | Pedidos que se cancelaron porque la comida duró demasiado tiempo en el mostrador y nadie la recogió.    |
| **Cancelaciones por accidente o falla**   |   $N_{\text{canc\_inc}}(t)$   | Pedidos que no se pudieron entregar por algún imprevisto en el camino (pinchazo, choque, etc.).          |

---

## 2. Parámetros del Sistema (Valores y reglas con las que se configura el modelo)

| Nombre                                              |             Símbolo             | ¿Qué significa en palabras simples?                                                                                            |
| :-------------------------------------------------- | :------------------------------: | :------------------------------------------------------------------------------------------------------------------------------- |
| **Frecuencia de pedidos**                     |   $\lambda(t)$ / $\lambda$   | Cuántos pedidos hacen los clientes por minuto según la hora del día (pocos en la mañana, muchos en almuerzo y cena).         |
| **Ritmo de conexión de repartidores**        |  $\lambda_{\text{login}}(t)$  | Cuántos repartidores se conectan a trabajar por minuto según la hora.                                                          |
| **Ritmo de atención teórico**               |             $\mu$             | Cuántos pedidos es capaz de despachar un repartidor por minuto en el modelo matemático básico.                                |
| **Tiempo de preparación de comida**          |      $T_{\text{cocina}}$      | Minutos que tarda el restaurante en cocinar un plato (varía de forma aleatoria según el pedido).                               |
| **Promedio base de cocina**                   |          $\mu_{\ln}$          | Parámetro que define el tiempo promedio estándar de cocción.                                                                  |
| **Variabilidad de cocina**                    |         $\sigma_{\ln}$         | Parámetro que define qué tan disparejos son los tiempos de cocina (platos rápidos vs. platos demorados).                      |
| **Fogones por restaurante**                   |             $k_r$             | Cantidad de fogones que tiene un restaurante específico (entre 3 y 6).                                                          |
| **Total de fogones en la ciudad**             |              $K$              | Suma de todos los fogones de los 10 restaurantes (límite físico de la red: 47 fogones).                                        |
| **Máxima comida por minuto**                 | $\lambda_{\text{cocina\_max}}$ | La mayor cantidad de pedidos que toda la red de restaurantes puede cocinar por minuto si todos los fogones están al 100%.       |
| **Velocidad del repartidor**                  |        $V_{\text{rep}}$        | Rapidez promedio a la que se mueve el repartidor en su moto o bicicleta por la ciudad.                                           |
| **Desvío vial de las calles**                |             $\tau$             | Factor que tiene en cuenta que las calles tienen curvas y desvíos (no se viaja en línea recta).                                |
| **Paciencia del cliente**                     |       $T_{\text{canc}}$       | Tiempo máximo que un cliente está dispuesto a esperar antes de enojarse y cancelar su pedido.                                  |
| **Crecimiento de impaciencia**                |             $k_w$             | Parámetro que indica cómo la probabilidad de que el cliente cancele se dispara a medida que pasa el tiempo.                    |
| **Escala de impaciencia**                     |          $\lambda_w$          | Parámetro que fija el rango general de paciencia promedio de las personas.                                                      |
| **Batería con la que arranca el repartidor** |   $\text{Bat}_{\text{ini}}$   | Porcentaje de batería que tiene el celular del conductor al momento de empezar su turno.                                        |
| **Gasto de batería viajando**                |     $r_{\text{bat\_ruta}}$     | Porcentaje de batería que gasta el celular por cada minuto en movimiento con GPS y pantalla encendida.                          |
| **Gasto de batería quieto**                  |    $r_{\text{bat\_espera}}$    | Porcentaje de batería que gasta el celular por minuto mientras el repartidor espera quieto un pedido.                           |
| **Batería mínima de seguridad**             |   $\text{Bat}_{\text{min}}$   | Nivel mínimo de batería (15%) por debajo del cual la app no le da más pedidos al repartidor para que no se apague el celular. |
| **Límite de turno continuo**                 |    $T_{\text{turno\_max}}$    | Tiempo máximo que un repartidor puede trabajar de corrido en un día (regla para evitar fatiga: 6 horas).                       |
| **Margen de anticipación (Buffer)**          |   $\Delta t_{\text{buffer}}$   | Minutos de anticipación con los que se manda a llamar al repartidor para que llegue justo cuando el plato sale del fogón.      |
| **Tiempo para aceptar la oferta**             |    $t_{\text{oferta\_max}}$    | Segundos que tiene el repartidor para tocar "Aceptar pedido" en su celular antes de que se lo ofrezcan a otro (45 s).            |
| **Tiempo de enfriamiento máximo**            |    $t_{\text{limbo\_max}}$    | Tiempo máximo que un plato puede esperar en mostrador (20 min) antes de desecharse por enfriamiento.                            |
| **Bono de pago urgente**                      |   $\gamma_{\text{urgente}}$   | Aumento porcentual de tarifa (+20%) que se le paga al repartidor para que acepte rápido un pedido que ya está listo.           |
| **Tamaño de la ciudad**                      |      $L_{\text{ciudad}}$      | Ancho y alto del mapa urbano donde se hacen las entregas ($6 \times 6\text{ km}$).                                             |
| **Conexiones fijas a la base de datos**       |      $\text{pool\_size}$      | Número de conexiones fijas que el software mantiene abiertas hacia PostgreSQL para atender peticiones.                          |
| **Conexiones extra por alta demanda**         |     $\text{max\_overflow}$     | Conexiones adicionales que el sistema abre temporalmente si entran muchos usuarios a la vez.                                     |
| **Tope máximo de conexiones al sistema**     |      $C_{\text{bd\_max}}$      | Límite máximo de conexiones que el servidor de base de datos soporta al mismo tiempo (30 conexiones).                          |

---

## 3. Momentos y Tiempos Clave (¿Qué hitos marcan el viaje de una orden?)

| Nombre                                                    |           Símbolo           | ¿Qué significa en palabras simples?                                                                    |
| :-------------------------------------------------------- | :---------------------------: | :------------------------------------------------------------------------------------------------------- |
| **Hora del pedido**                                 |    $t_{\text{creacion}}$    | Minuto exacto en el que el cliente oprime el botón de comprar en la app.                                |
| **Hora de entrada al fogón**                       | $t_{\text{inicio\_cocina}}$ | Momento en el que el cocinero empieza a preparar el pedido.                                              |
| **Hora de salida a mostrador**                      |     $t_{\text{listo}}$     | Momento en el que el plato se termina de cocinar y se deja en la barra de entrega.                       |
| **Hora de llamado al repartidor**                   |    $t_{\text{despacho}}$    | Momento en el que el sistema le envía la notificación al repartidor para asignarle el pedido.          |
| **Hora de aceptación**                             |   $t_{\text{aceptacion}}$   | Momento en el que el repartidor acepta el viaje en su pantalla.                                          |
| **Hora de llegada al restaurante**                  |  $t_{\text{arribo\_rep}}$  | Momento en el que el repartidor llega físicamente a la puerta del local.                                |
| **Hora de recogida**                                |    $t_{\text{recogida}}$    | Momento en el que el repartidor toma la bolsa de comida y arranca hacia la casa del cliente.             |
| **Hora de entrega**                                 |   $t_{\text{entregado}}$   | Momento en el que el repartidor le entrega el paquete en la mano al cliente.                             |
| **Hora de inicio de turno**                         |     $t_{\text{login}}$     | Hora a la que el repartidor se conecta por primera vez en el día.                                       |
| **Hora de fin de turno**                            |     $t_{\text{logout}}$     | Hora a la que el repartidor apaga la aplicación y deja de trabajar.                                     |
| **Viaje hacia el restaurante**                      |  $t_{\text{viaje\_local}}$  | Cuántos minutos tarda el repartidor en llegar desde donde estaba hasta el restaurante.                  |
| **Viaje hacia la casa del cliente**                 | $t_{\text{viaje\_cliente}}$ | Cuántos minutos tarda el repartidor en ir desde el restaurante hasta la dirección de entrega.          |
| **Estimado de cuándo estará lista la comida**     | $\text{ETA}_{\text{listo}}$ | Cálculo de a qué hora terminará de cocinarse el plato para coordinar la llegada del repartidor.       |
| **Tiempo perdido del repartidor en el restaurante** |  $T_{\text{espera\_rest}}$  | Minutos que el repartidor se queda quieto en el restaurante esperando a que la comida salga del fogón.  |
| **Tiempo de enfriamiento en mostrador**             |   $T_{\text{mostrador}}$   | Minutos que la comida ya cocinada se queda enfriando en la barra hasta que llega el repartidor por ella. |
| **Tiempo total de entrega**                         |     $W_{\text{total}}$     | Minutos totales que pasaron desde que el cliente pidió hasta que recibió su comida.                    |

---

## 4. Indicadores de Rendimiento y Resultados (¿Cómo medimos si el sistema funciona bien?)

| Nombre                                                                |             Símbolo             | ¿Qué significa en palabras simples?                                                                            |
| :-------------------------------------------------------------------- | :-------------------------------: | :--------------------------------------------------------------------------------------------------------------- |
| **Ocupación de los fogones**                                   |     $\rho_{\text{cocina}}$     | Porcentaje del tiempo que las cocinas se la pasan cocinando (si es muy alto, hay congestión).                   |
| **Ocupación de los repartidores**                              |       $\rho_{\text{rep}}$       | Porcentaje del tiempo que los repartidores pasan trabajando en entregas y no parados sin hacer nada.             |
| **Probabilidad de local vacío**                                |              $P_0$              | Probabilidad matemática de que no haya ningún pedido en cocina en un momento dado.                             |
| **Probabilidad de tener que hacer fila**                        |              $P_w$              | Probabilidad de que un pedido nuevo tenga que esperar porque todos los fogones están ocupados.                  |
| **Promedio de pedidos en fila**                                 |              $L_q$              | Cantidad promedio de pedidos esperando fogón libre en un momento cualquiera.                                    |
| **Promedio de pedidos en el restaurante**                       |               $L$               | Cantidad promedio de pedidos que hay en total (los que están en fila más los que se están cocinando).         |
| **Tiempo promedio de espera en fila**                           |              $W_q$              | Minutos promedio que un pedido tiene que esperar antes de que empiecen a cocinarlo.                              |
| **Tiempo promedio total en el restaurante**                     |               $W$               | Minutos promedio que dura un pedido dentro del local (espera en fila más el tiempo de cocción).                |
| **Tiempo de entrega en el peor de los casos (Percentil 95)**    |     $W_{\text{total\_p95}}$     | Tiempo en el que se entrega el 95% de los pedidos (es decir, casi todos llegan en menos de este tiempo).         |
| **Tiempo promedio que el repartidor pierde esperando**          | $\bar{T}_{\text{espera\_rest}}$ | Promedio de minutos que los repartidores pierden sin hacer nada en los locales esperando la comida.              |
| **Tiempo máximo que la comida espera en barra (Percentil 95)** |   $T_{\text{mostrador\_p95}}$   | Tiempo que la comida espera en mostrador para el 95% de los casos (mide si la comida llega caliente).            |
| **Porcentaje de pedidos cancelados**                            |        $P_{\text{canc}}$        | Qué porcentaje de los pedidos se pierden porque el cliente se cansó de esperar o porque nadie los recogió.    |
| **Rapidez de respuesta del software (Latencia)**                |      $T_{\text{lat\_api}}$      | Milisegundos que tarda el servidor en responder cuando la app le pide información.                              |
| **Peor tiempo de respuesta del servidor (Percentil 99)**        |   $T_{\text{lat\_api\_p99}}$   | El tiempo de respuesta más lento que experimenta el 1% de las peticiones cuando el servidor está bajo estrés. |
| **Peticiones por segundo del software**                         |          $\text{RPS}$          | Cantidad de operaciones o consultas que la aplicación es capaz de atender cada segundo.                         |
| **Uso de procesador (CPU)**                                     |        $\text{CPU}_{\%}$        | Qué tanto se está esforzando el procesador de la computadora al correr el sistema.                             |
| **Uso de memoria (RAM)**                                        |    $\text{RAM}_{\text{RSS}}$    | Cantidad de memoria de la computadora que el software necesita para estar funcionando.                           |
