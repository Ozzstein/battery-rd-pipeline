"""
Test Template for Battery RUL Methods

Copy this template and adapt for each new method.
Run with: pytest tests/test_<method_name>.py -v
"""

import pytest
import numpy as np
import torch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.development.templates.method_template import LSTMBaseline


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_data():
    """Generate sample battery data for testing"""
    np.random.seed(42)
    n_samples = 500
    n_features = 10
    
    X = np.random.randn(n_samples, n_features).astype(np.float32)
    y = np.abs(np.random.randn(n_samples) * 100 + 500).astype(np.float32)  # RUL > 0
    
    return X, y


@pytest.fixture
def sample_data_split(sample_data):
    """Create train/val/test split"""
    X, y = sample_data
    
    n_train = int(0.6 * len(X))
    n_val = int(0.2 * len(X))
    
    X_train = X[:n_train]
    y_train = y[:n_train]
    
    X_val = X[n_train:n_train+n_val]
    y_val = y[n_train:n_train+n_val]
    
    X_test = X[n_train+n_val:]
    y_test = y[n_train+n_val:]
    
    return {
        'train': (X_train, y_train),
        'val': (X_val, y_val),
        'test': (X_test, y_test)
    }


@pytest.fixture
def trained_model(sample_data_split):
    """Create and train a model for testing"""
    X_train, y_train = sample_data_split['train']
    X_val, y_val = sample_data_split['val']
    
    model = LSTMBaseline(
        config={
            'input_dim': X_train.shape[1],
            'epochs': 5,  # Small for testing
            'batch_size': 16,
            'hidden_dim': 32,
        }
    )
    
    history = model.fit(X_train, y_train, X_val, y_val)
    
    return model, history


# =============================================================================
# Initialization Tests
# =============================================================================

class TestInitialization:
    """Test model initialization"""
    
    def test_model_creation(self, sample_data):
        """Test that model can be created"""
        X, y = sample_data
        input_dim = X.shape[1]
        
        model = LSTMBaseline(config={'input_dim': input_dim})
        
        assert model is not None
        assert model.model is not None
        assert model.device is not None
    
    def test_parameter_count(self, sample_data):
        """Test that model has reasonable number of parameters"""
        X, y = sample_data
        input_dim = X.shape[1]
        
        model = LSTMBaseline(config={
            'input_dim': input_dim,
            'hidden_dim': 64,
            'num_layers': 2
        })
        
        n_params = model.count_parameters()
        assert n_params > 0
        assert n_params < 1_000_000  # Sanity check
    
    def test_device_placement(self, sample_data):
        """Test that model is on correct device"""
        X, y = sample_data
        input_dim = X.shape[1]
        
        model = LSTMBaseline(config={'input_dim': input_dim})
        
        expected_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        assert model.device == expected_device


# =============================================================================
# Training Tests
# =============================================================================

class TestTraining:
    """Test model training"""
    
    def test_training_reduces_loss(self, sample_data_split):
        """Test that training reduces loss"""
        X_train, y_train = sample_data_split['train']
        X_val, y_val = sample_data_split['val']
        
        model = LSTMBaseline(config={
            'input_dim': X_train.shape[1],
            'epochs': 20,
        })
        
        history = model.fit(X_train, y_train, X_val, y_val)
        
        # Loss should decrease
        assert len(history['train_loss']) == 20
        assert history['train_loss'][-1] < history['train_loss'][0]
    
    def test_training_sets_flag(self, sample_data_split):
        """Test that training sets is_trained flag"""
        X_train, y_train = sample_data_split['train']
        
        model = LSTMBaseline(config={'input_dim': X_train.shape[1]})
        assert not model.is_trained
        
        model.fit(X_train, y_train)
        assert model.is_trained
    
    def test_training_history_structure(self, sample_data_split):
        """Test that training history has correct structure"""
        X_train, y_train = sample_data_split['train']
        
        model = LSTMBaseline(config={'input_dim': X_train.shape[1], 'epochs': 10})
        history = model.fit(X_train, y_train)
        
        assert 'train_loss' in history
        assert 'epochs' in history
        assert len(history['train_loss']) == 10
        assert len(history['epochs']) == 10


# =============================================================================
# Prediction Tests
# =============================================================================

class TestPrediction:
    """Test model prediction"""
    
    def test_prediction_shape(self, trained_model, sample_data_split):
        """Test that predictions have correct shape"""
        model, _ = trained_model
        X_test, y_test = sample_data_split['test']
        
        predictions = model.predict(X_test)
        
        assert predictions.shape[0] > 0
        assert predictions.shape[0] <= len(X_test)
    
    def test_prediction_range(self, trained_model, sample_data_split):
        """Test that predictions are in reasonable range"""
        model, _ = trained_model
        X_test, y_test = sample_data_split['test']
        
        predictions = model.predict(X_test)
        
        # RUL should be positive
        assert np.all(predictions > 0)
        
        # RUL should be in reasonable range (not too extreme)
        assert np.all(predictions < 2000)  # Sanity check
    
    def test_prediction_requires_training(self, sample_data):
        """Test that prediction requires trained model"""
        X, y = sample_data
        model = LSTMBaseline(config={'input_dim': X.shape[1]})
        
        with pytest.raises(RuntimeError):
            model.predict(X)


# =============================================================================
# Save/Load Tests
# =============================================================================

class TestSaveLoad:
    """Test model saving and loading"""
    
    def test_save_creates_files(self, trained_model, tmp_path):
        """Test that save creates expected files"""
        model, _ = trained_model
        save_path = tmp_path / 'test_model'
        
        model.save(str(save_path))
        
        assert (save_path / 'model.pt').exists()
        assert (save_path / 'config.json').exists()
    
    def test_load_restores_model(self, trained_model, sample_data_split, tmp_path):
        """Test that loaded model produces same predictions"""
        model, _ = trained_model
        X_test, y_test = sample_data_split['test']
        
        # Get predictions from original model
        pred_original = model.predict(X_test)
        
        # Save and load
        save_path = tmp_path / 'test_model'
        model.save(str(save_path))
        
        loaded_model = LSTMBaseline()
        loaded_model.load(str(save_path))
        
        # Get predictions from loaded model
        pred_loaded = loaded_model.predict(X_test)
        
        # Should be identical
        np.testing.assert_array_almost_equal(pred_original, pred_loaded)
    
    def test_load_restores_training_flag(self, trained_model, tmp_path):
        """Test that loaded model has is_trained flag"""
        model, _ = trained_model
        
        save_path = tmp_path / 'test_model'
        model.save(str(save_path))
        
        loaded_model = LSTMBaseline()
        assert not loaded_model.is_trained
        
        loaded_model.load(str(save_path))
        assert loaded_model.is_trained


# =============================================================================
# Normalization Tests
# =============================================================================

class TestNormalization:
    """Test feature normalization"""
    
    def test_normalization_stored(self, sample_data_split):
        """Test that normalization stats are stored during training"""
        X_train, y_train = sample_data_split['train']
        
        model = LSTMBaseline(config={'input_dim': X_train.shape[1]})
        model.fit(X_train, y_train)
        
        assert hasattr(model, 'feature_mean')
        assert hasattr(model, 'feature_std')
        assert hasattr(model, 'target_mean')
        assert hasattr(model, 'target_std')
    
    def test_normalization_shapes(self, sample_data_split):
        """Test that normalization stats have correct shapes"""
        X_train, y_train = sample_data_split['train']
        
        model = LSTMBaseline(config={'input_dim': X_train.shape[1]})
        model.fit(X_train, y_train)
        
        assert model.feature_mean.shape == (X_train.shape[1],)
        assert model.feature_std.shape == (X_train.shape[1],)
        assert np.isscalar(model.target_mean)
        assert np.isscalar(model.target_std)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    def test_full_pipeline(self, sample_data):
        """Test complete training and prediction pipeline"""
        X, y = sample_data
        
        # Split
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # Train
        model = LSTMBaseline(config={
            'input_dim': X_train.shape[1],
            'epochs': 10,
        })
        history = model.fit(X_train, y_train)
        
        # Predict
        predictions = model.predict(X_test)
        
        # Evaluate
        mae = np.mean(np.abs(predictions - y_test[len(X_test)-len(predictions):]))
        
        assert mae > 0
        assert mae < 500  # Sanity check
    
    def test_config_roundtrip(self, trained_model, tmp_path):
        """Test that config can be saved and loaded"""
        model, _ = trained_model
        
        save_path = tmp_path / 'test_model'
        model.save(str(save_path))
        
        loaded_model = LSTMBaseline()
        loaded_model.load(str(save_path))
        
        # Compare configs
        orig_config = model.get_config()
        loaded_config = loaded_model.get_config()
        
        assert orig_config['hidden_dim'] == loaded_config['hidden_dim']
        assert orig_config['num_layers'] == loaded_config['num_layers']


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
