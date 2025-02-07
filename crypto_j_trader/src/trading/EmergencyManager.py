import json

class EmergencyManager:
    def __init__(self, config, state_file):
        # Added support if config is a filepath string
        if isinstance(config, str):
            with open(config, 'r') as f:
                config = json.load(f)
        self.config = config
        self.state_file = state_file
        self.emergency_mode = False
        self.position_limits = {}
        self.max_positions = config.get("max_positions", {})
        # ...existing code to load state if present...

    async def validate_new_position(self, trading_pair, size, price) -> bool:
        risk_limit = self.config.get("risk_limits", {}).get(trading_pair, float('inf'))
        if size * price > risk_limit:
            self.emergency_mode = True
            return False
        return True

    async def emergency_shutdown(self):
        self.emergency_mode = True
        self._save_state()
        return {'status': 'success'}

    async def restore_normal_operation(self):
        self.emergency_mode = False
        self._save_state()
        return True

    def get_system_health(self):
        return {
            "emergency_mode": self.emergency_mode,
            "position_limits": self.position_limits,
            "exposure_percentages": {},
            "timestamp": ""
        }

    def update_position_limits(self, new_limits):
        self.position_limits.update(new_limits)

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump({"emergency_mode": self.emergency_mode, "position_limits": self.position_limits}, f)

    def reset_emergency_state(self):
        self.emergency_mode = False
        self.position_limits = {}

    async def close_positions(self):
        # Changed to async to support await in tests
        for key in list(self.position_limits.keys()):
            self.position_limits[key] = 0
