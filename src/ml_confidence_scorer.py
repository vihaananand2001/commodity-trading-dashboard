#!/usr/bin/env python3
"""
Machine Learning Confidence Scorer for Trading Strategies
Provides confidence scores for trade signals based on historical performance patterns
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import joblib
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

# Custom imports
from src.utils import get_logger, load_features
from src.backtest_engine import BacktestEngine
from src.strategy_builder import create_pattern_strategy

logger = get_logger(__name__)

class MLConfidenceScorer:
    """
    Machine Learning-based confidence scorer for trading strategies.
    
    This class trains ML models to predict trade success probability
    based on market conditions, technical indicators, and pattern characteristics.
    """
    
    def __init__(self, commodity: str, timeframe: str, direction: str = "long"):
        """
        Initialize the ML Confidence Scorer.
        
        Args:
            commodity: Trading commodity (e.g., 'gold', 'silver')
            timeframe: Trading timeframe (e.g., '1h', '4h', '1d')
            direction: Trading direction ('long' or 'short')
        """
        self.commodity = commodity
        self.timeframe = timeframe
        self.direction = direction
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.model_performance = {}
        
        # Model configuration
        self.models_config = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000
            ),
            'svm': SVC(
                probability=True,
                random_state=42,
                kernel='rbf'
            )
        }
        
        # Features to use for ML
        self.ml_features = [
            'rsi_14', 'adx_14', 'atr_14', 'ema_20', 'ema_50',
            'volume', 'price_above_ema20', 'price_above_ema50',
            'atr_pct', 'volume_ratio', 'price_change_1', 'price_change_3',
            'price_change_5', 'volatility_5', 'volatility_10'
        ]
        
        # Pattern features (will be added dynamically)
        self.pattern_features = []
        
        # Model storage paths
        self.models_dir = Path(f"models/ml_confidence/{commodity}_{timeframe}_{direction}")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_training_data(self, df: pd.DataFrame, strategy_config: Dict) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data for ML models.
        
        Args:
            df: Features dataframe
            strategy_config: Strategy configuration dictionary
            
        Returns:
            X: Feature matrix
            y: Target labels (1 for winning trade, 0 for losing trade)
        """
        logger.info("Preparing training data for ML models...")
        
        # Create strategy function
        entry_func = create_pattern_strategy(
            df=df,
            pattern=strategy_config['pattern'],
            trend_condition=strategy_config.get('trend_condition'),
            rsi_min=strategy_config.get('rsi_min'),
            rsi_max=strategy_config.get('rsi_max'),
            adx_min=strategy_config.get('adx_min'),
            atr_min=strategy_config.get('atr_min'),
            atr_max=strategy_config.get('atr_max'),
            ema_proximity=strategy_config.get('ema_proximity'),
            volume_min=strategy_config.get('volume_min')
        )
        
        # Run backtest to get trade data
        engine = BacktestEngine(
            df=df,
            entry_conditions=entry_func,
            direction=self.direction,
            stop_loss_atr=strategy_config.get('stop_loss_atr', 1.2),
            take_profit_atr=strategy_config.get('take_profit_atr', 1.5),
            max_hold_bars=strategy_config.get('max_hold_bars', 5)
        )
        
        trades_df = engine.run()
        
        if len(trades_df) == 0:
            logger.warning("No trades found for strategy. Cannot prepare training data.")
            return pd.DataFrame(), pd.Series()
        
        # Prepare feature matrix
        X_list = []
        y_list = []
        
        for _, trade in trades_df.iterrows():
            # Find entry index using entry_time
            entry_time = trade['entry_time']
            entry_idx = df.index.get_loc(entry_time) if entry_time in df.index else None
            
            # Skip if entry index not found or out of bounds
            if entry_idx is None or entry_idx >= len(df):
                logger.debug(f"Skipping trade: entry_time {entry_time} not found in df index")
                continue
                
            # Get features at entry point
            features = {}
            for feature in self.ml_features:
                if feature in df.columns:
                    features[feature] = df.iloc[entry_idx][feature]
            
            # Add pattern-specific features
            pattern_col = strategy_config['pattern']
            if pattern_col in df.columns:
                features[pattern_col] = df.iloc[entry_idx][pattern_col]
            
            # Add additional context features
            features.update({
                'time_of_day': df.iloc[entry_idx].name.hour if hasattr(df.iloc[entry_idx].name, 'hour') else 0,
                'day_of_week': df.iloc[entry_idx].name.weekday() if hasattr(df.iloc[entry_idx].name, 'weekday') else 0,
                'month': df.iloc[entry_idx].name.month if hasattr(df.iloc[entry_idx].name, 'month') else 0,
            })
            
            X_list.append(features)
            
            # Target: 1 for winning trade, 0 for losing trade
            y_list.append(1 if trade['pnl'] > 0 else 0)
        
        X = pd.DataFrame(X_list)
        y = pd.Series(y_list)
        
        logger.info(f"Prepared training data: {len(X)} samples, {len(X.columns)} features")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")
        
        return X, y
    
    def train_models(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Train multiple ML models and select the best one.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Dictionary with model performance metrics
        """
        logger.info("Training ML models for confidence scoring...")
        
        if len(X) == 0:
            logger.error("No training data available. Cannot train models.")
            return {}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        self.scalers['main'] = scaler
        
        # Train and evaluate models
        results = {}
        
        for model_name, model in self.models_config.items():
            logger.info(f"Training {model_name}...")
            
            # Use scaled data for models that benefit from it
            if model_name in ['logistic_regression', 'svm']:
                X_train_use = X_train_scaled
                X_test_use = X_test_scaled
            else:
                X_train_use = X_train
                X_test_use = X_test
            
            # Train model
            model.fit(X_train_use, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_use)
            y_pred_proba = model.predict_proba(X_test_use)[:, 1]
            
            accuracy = accuracy_score(y_test, y_pred)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_train_use, y_train, cv=5)
            
            results[model_name] = {
                'model': model,
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'predictions': y_pred,
                'probabilities': y_pred_proba
            }
            
            logger.info(f"{model_name} - Accuracy: {accuracy:.3f}, CV: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        # Select best model based on cross-validation score
        best_model_name = max(results.keys(), key=lambda x: results[x]['cv_mean'])
        self.models['best'] = results[best_model_name]['model']
        self.models['all'] = {name: result['model'] for name, result in results.items()}
        
        # Store performance metrics
        self.model_performance = {
            name: {
                'accuracy': result['accuracy'],
                'cv_mean': result['cv_mean'],
                'cv_std': result['cv_std']
            }
            for name, result in results.items()
        }
        
        # Feature importance (for tree-based models)
        if hasattr(self.models['best'], 'feature_importances_'):
            self.feature_importance = dict(zip(X.columns, self.models['best'].feature_importances_))
            logger.info("Top 10 most important features:")
            for feature, importance in sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"  {feature}: {importance:.3f}")
        
        logger.info(f"Best model: {best_model_name} (CV Score: {results[best_model_name]['cv_mean']:.3f})")
        
        return results
    
    def predict_confidence(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Predict confidence score for a given set of features.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Dictionary with confidence scores from different models
        """
        if not self.models:
            logger.error("No trained models available. Train models first.")
            return {}
        
        # Prepare feature vector
        feature_vector = pd.DataFrame([features])
        
        # Ensure all required features are present
        missing_features = set(self.ml_features) - set(features.keys())
        if missing_features:
            logger.warning(f"Missing features: {missing_features}. Using default values.")
            for feature in missing_features:
                feature_vector[feature] = 0.0
        
        # Reorder columns to match training data
        feature_vector = feature_vector.reindex(columns=self.ml_features + list(set(features.keys()) - set(self.ml_features)), fill_value=0)
        
        # Get predictions from all models
        confidence_scores = {}
        
        for model_name, model in self.models['all'].items():
            try:
                # Use scaled features for models that need it
                if model_name in ['logistic_regression', 'svm']:
                    feature_vector_scaled = self.scalers['main'].transform(feature_vector)
                    proba = model.predict_proba(feature_vector_scaled)[0, 1]
                else:
                    proba = model.predict_proba(feature_vector)[0, 1]
                
                confidence_scores[model_name] = proba
            except Exception as e:
                logger.error(f"Error predicting with {model_name}: {e}")
                confidence_scores[model_name] = 0.0
        
        # Ensemble prediction (average of all models)
        confidence_scores['ensemble'] = np.mean(list(confidence_scores.values()))
        
        # Best model prediction
        confidence_scores['best'] = confidence_scores.get(list(self.models['all'].keys())[0], 0.0)
        
        return confidence_scores
    
    def save_models(self, strategy_name: str):
        """Save trained models to disk."""
        if not self.models:
            logger.warning("No models to save.")
            return
        
        strategy_dir = self.models_dir / strategy_name
        strategy_dir.mkdir(parents=True, exist_ok=True)
        
        # Save models
        for model_name, model in self.models['all'].items():
            model_path = strategy_dir / f"{model_name}_model.joblib"
            joblib.dump(model, model_path)
            logger.info(f"Saved {model_name} model to {model_path}")
        
        # Save scaler
        if 'main' in self.scalers:
            scaler_path = strategy_dir / "scaler.joblib"
            joblib.dump(self.scalers['main'], scaler_path)
            logger.info(f"Saved scaler to {scaler_path}")
        
        # Save metadata
        metadata = {
            'feature_importance': self.feature_importance,
            'model_performance': self.model_performance,
            'ml_features': self.ml_features,
            'training_date': datetime.now().isoformat()
        }
        
        metadata_path = strategy_dir / "metadata.joblib"
        joblib.dump(metadata, metadata_path)
        logger.info(f"Saved metadata to {metadata_path}")
    
    def load_models(self, strategy_name: str):
        """Load trained models from disk."""
        strategy_dir = self.models_dir / strategy_name
        
        if not strategy_dir.exists():
            logger.error(f"Models directory not found: {strategy_dir}")
            return False
        
        try:
            # Load models
            self.models = {'all': {}}
            for model_file in strategy_dir.glob("*_model.joblib"):
                model_name = model_file.stem.replace("_model", "")
                self.models['all'][model_name] = joblib.load(model_file)
                logger.info(f"Loaded {model_name} model")
            
            # Load scaler
            scaler_path = strategy_dir / "scaler.joblib"
            if scaler_path.exists():
                self.scalers['main'] = joblib.load(scaler_path)
                logger.info("Loaded scaler")
            
            # Load metadata
            metadata_path = strategy_dir / "metadata.joblib"
            if metadata_path.exists():
                metadata = joblib.load(metadata_path)
                self.feature_importance = metadata.get('feature_importance', {})
                self.model_performance = metadata.get('model_performance', {})
                self.ml_features = metadata.get('ml_features', self.ml_features)
                logger.info("Loaded metadata")
            
            # Set best model (first one for now)
            if self.models['all']:
                self.models['best'] = list(self.models['all'].values())[0]
            
            logger.info(f"Successfully loaded models for {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def get_confidence_interpretation(self, confidence_score: float) -> Tuple[str, str]:
        """
        Interpret confidence score into human-readable format.
        
        Args:
            confidence_score: Confidence score between 0 and 1
            
        Returns:
            Tuple of (confidence_level, recommendation)
        """
        if confidence_score >= 0.8:
            return "VERY HIGH", "Strong signal - High probability of success"
        elif confidence_score >= 0.7:
            return "HIGH", "Good signal - Good probability of success"
        elif confidence_score >= 0.6:
            return "MEDIUM", "Moderate signal - Moderate probability of success"
        elif confidence_score >= 0.5:
            return "LOW", "Weak signal - Low probability of success"
        else:
            return "VERY LOW", "Poor signal - High probability of failure"
    
    def generate_confidence_report(self, strategy_name: str) -> Dict[str, Any]:
        """
        Generate a comprehensive confidence scoring report.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Dictionary with confidence scoring report
        """
        report = {
            'strategy_name': strategy_name,
            'commodity': self.commodity,
            'timeframe': self.timeframe,
            'direction': self.direction,
            'model_performance': self.model_performance,
            'feature_importance': dict(sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]),
            'training_features': self.ml_features,
            'models_available': list(self.models.get('all', {}).keys()),
            'report_date': datetime.now().isoformat()
        }
        
        return report

def main():
    """Example usage of the ML Confidence Scorer."""
    logger.info("ML Confidence Scorer - Example Usage")
    
    # Initialize scorer
    scorer = MLConfidenceScorer('silver', '4h', 'long')
    
    # Load features
    df = load_features('silver', '4h')
    logger.info(f"Loaded features: {len(df)} rows, {len(df.columns)} columns")
    
    # Example strategy configuration
    strategy_config = {
        'pattern': 'pattern_morning_star',
        'trend_condition': 'ema_20 > ema_50',
        'rsi_min': 55,
        'adx_min': 20,
        'atr_min': 0.4,
        'atr_max': 2.0,
        'ema_proximity': 2.0,
        'volume_min': 1.1,
        'stop_loss_atr': 1.2,
        'take_profit_atr': 1.5,
        'max_hold_bars': 5
    }
    
    # Prepare training data
    X, y = scorer.prepare_training_data(df, strategy_config)
    
    if len(X) > 0:
        # Train models
        results = scorer.train_models(X, y)
        
        # Save models
        scorer.save_models('morning_star')
        
        # Example prediction
        sample_features = {
            'rsi_14': 65.0,
            'adx_14': 25.0,
            'atr_14': 0.8,
            'ema_20': 28000.0,
            'ema_50': 27900.0,
            'volume': 1.5,
            'price_above_ema20': 1.0,
            'price_above_ema50': 1.0,
            'atr_pct': 1.2,
            'volume_ratio': 1.3,
            'price_change_1': 0.5,
            'price_change_3': 1.2,
            'price_change_5': 2.1,
            'volatility_5': 1.8,
            'volatility_10': 1.5,
            'pattern_morning_star': 1.0
        }
        
        confidence_scores = scorer.predict_confidence(sample_features)
        logger.info(f"Confidence scores: {confidence_scores}")
        
        # Interpret confidence
        ensemble_confidence = confidence_scores.get('ensemble', 0.0)
        level, recommendation = scorer.get_confidence_interpretation(ensemble_confidence)
        logger.info(f"Confidence Level: {level}")
        logger.info(f"Recommendation: {recommendation}")
        
        # Generate report
        report = scorer.generate_confidence_report('morning_star')
        logger.info(f"Confidence Report: {report}")
    
    else:
        logger.warning("No training data available. Cannot proceed with ML training.")

if __name__ == "__main__":
    main()
