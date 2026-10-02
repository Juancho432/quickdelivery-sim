from pydantic import BaseModel, Field


class SystemConfiguration:
    def __init__(self):
        self.active_dispatch_policy: str = "synchronized"  # "synchronized" o "greedy"
        self.buffer_delta_t_min: float = 2.0               # Margen de holgura (Pregunta 4)
        self.max_shift_duration_min: float = 360.0         # Límite duro de turno (6h)
        self.anti_limbo_max_counter_min: float = 20.0      # Protocolo anti-limbo (D-07)
        self.urgency_bonus_multiplier: float = 1.20        # Bono de emergencia (+20%)
        self.min_battery_threshold_pct: float = 15.0       # Reserva crítica de batería

    def to_dict(self):
        return {
            "active_dispatch_policy": self.active_dispatch_policy,
            "buffer_delta_t_min": self.buffer_delta_t_min,
            "max_shift_duration_min": self.max_shift_duration_min,
            "anti_limbo_max_counter_min": self.anti_limbo_max_counter_min,
            "urgency_bonus_multiplier": self.urgency_bonus_multiplier,
            "min_battery_threshold_pct": self.min_battery_threshold_pct
        }

    def update(self, **kwargs):
        for key, val in kwargs.items():
            if hasattr(self, key) and val is not None:
                setattr(self, key, val)
        return self.to_dict()


# Instancia singleton accesible en todo el runtime
system_config = SystemConfiguration()
