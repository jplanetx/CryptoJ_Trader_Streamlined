# Emergency Manager Implementation Update

## Changes Implemented

### 1. validate_new_position Method
```python
class EmergencyManager:
    async def validate_new_position(self, symbol: str, size: float, price: float) -> dict:
        """
        Validates a new position against risk limits and emergency conditions.
        
        Args:
            symbol: Trading pair symbol
            size: Position size
            price: Current price
            
        Returns:
            dict: Validation result with status and optional error message
        """
        try:
            # Check emergency mode
            if self.is_emergency_mode_active():
                return {
                    'status': 'error',
                    'error': 'Cannot open new positions during emergency mode'
                }
                
            # Get current positions
            current_positions = await self._get_current_positions()
            
            # Calculate total exposure
            total_exposure = sum(
                pos['size'] * pos['price'] 
                for pos in current_positions.values()
            )
            new_exposure = size * price
            
            # Check against risk limits
            if total_exposure + new_exposure > self.max_exposure:
                return {
                    'status': 'error',
                    'error': f'Position would exceed maximum exposure of {self.max_exposure}'
                }
                
            # Validate against risk manager
            risk_validation = await self.risk_manager.validate_position(
                symbol=symbol,
                size=size,
                price=price
            )
            
            if risk_validation['status'] != 'success':
                return risk_validation
                
            return {'status': 'success'}
            
        except Exception as e:
            logging.error(f"Position validation error: {e}")
            return {
                'status': 'error',
                'error': f'Validation failed: {str(e)}'
            }
```

### 2. JSON Persistence Fix
```python
async def _persist_emergency_state(self) -> None:
    """Persists emergency state to JSON with proper error handling"""
    try:
        state = {
            'emergency_mode': self._emergency_mode,
            'timestamp': datetime.utcnow().isoformat(),
            'reason': self._emergency_reason,
            'active_positions': self._positions
        }
        
        async with aiofiles.open(self.state_file, 'w') as f:
            await f.write(json.dumps(state, indent=2))
            await f.flush()
            os.fsync(f.fileno())
            
    except Exception as e:
        logging.error(f"Failed to persist emergency state: {e}")
        raise EmergencyStateError(f"State persistence failed: {e}")
```

### 3. State Consistency Improvements
```python
class EmergencyManager:
    def __init__(self, config: dict):
        self._emergency_mode = False
        self._emergency_reason = None
        self._state_lock = asyncio.Lock()
        self._positions = {}
        self.state_file = config.get('emergency_state_file', 'emergency_state.json')
        
    async def update_state(self, emergency_mode: bool, reason: str = None) -> None:
        """Thread-safe state update with persistence"""
        async with self._state_lock:
            self._emergency_mode = emergency_mode
            self._emergency_reason = reason
            await self._persist_emergency_state()
            
    async def recover_state(self) -> None:
        """Recovers state from persistent storage"""
        try:
            if not os.path.exists(self.state_file):
                return
                
            async with aiofiles.open(self.state_file, 'r') as f:
                content = await f.read()
                state = json.loads(content)
                
            async with self._state_lock:
                self._emergency_mode = state['emergency_mode']
                self._emergency_reason = state['reason']
                self._positions = state['active_positions']
                
        except Exception as e:
            logging.error(f"State recovery failed: {e}")
            raise EmergencyStateError(f"State recovery failed: {e}")
```

## Testing Status
- Position validation tests passing
- JSON persistence tests passing
- State consistency tests passing
- Integration tests successful

## Next Steps
1. Complete WebSocket handler implementation
2. Add comprehensive logging
3. Update documentation

## Notes
- Added thread-safe state management
- Improved error handling
- Enhanced persistence reliability
- Added state recovery mechanisms