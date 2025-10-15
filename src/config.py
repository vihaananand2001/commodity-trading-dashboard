"""
Configuration Loader
Loads and manages configuration from settings.yaml
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from utils import get_logger

logger = get_logger(__name__)

class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Default to config/settings.yaml relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "settings.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'objectives': {
                'max_drawdown_pct': 15.0,
                'min_profit_factor': 1.25,
                'min_win_rate': 60.0
            },
            'backtest': {
                'default_stop_loss_atr': 2.0,
                'default_take_profit_atr': 3.0,
                'default_max_hold_bars': None,
                'atr_column': 'atr_14'
            },
            'optimization': {
                'use_multiprocessing': True,
                'num_processes': None,
                'chunk_size': 64
            },
            'filters': {
                'min_trades': 10
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Example:
        --------
        config.get('objectives.max_drawdown_pct')
        config.get('backtest.default_stop_loss_atr')
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_commodities(self):
        """Get list of commodities"""
        return self.get('assets.commodities', ['gold', 'silver', 'copper'])
    
    def get_timeframes(self):
        """Get list of timeframes"""
        return self.get('assets.timeframes', ['1h', '4h', '1d'])
    
    def get_bullish_patterns(self):
        """Get bullish patterns"""
        return self.get('patterns.bullish', [])
    
    def get_bearish_patterns(self):
        """Get bearish patterns"""
        return self.get('patterns.bearish', [])
    
    def get_optimization_params(self) -> Dict:
        """Get optimization parameter ranges"""
        return self.get('optimization', {})
    
    def get_objectives(self) -> Dict:
        """Get trading objectives"""
        return self.get('objectives', {})

# Global config instance
_config = None

def get_config(config_path: Optional[str] = None) -> Config:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config

if __name__ == "__main__":
    config = get_config()
    print(f"Loaded config:")
    print(f"  Commodities: {config.get_commodities()}")
    print(f"  Timeframes: {config.get_timeframes()}")
    print(f"  Max DD: {config.get('objectives.max_drawdown_pct')}%")
    print(f"  Min PF: {config.get('objectives.min_profit_factor')}")




