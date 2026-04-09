"""
Battery RUL Estimation - Base Method Template

All RUL estimation methods should inherit from this base class
and implement the required methods.
"""

import os
import json
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class BaseRULMethod(ABC):
    """
    Abstract base class for all Battery RUL estimation methods.
    
    Subclasses must implement:
    - __init__(): Initialize model and hyperparameters
    - _build_model(): Create the neural network architecture
    - fit(): Train the model on training data
    - predict(): Make RUL predictions
    - save(): Save model weights and config
    - load(): Load model from disk
    """
    
    def __init__(self, config: Dict = None, **kwargs):
        """
        Initialize the RUL estimation method.
        
        Args:
            config: Hyperparameter configuration dict
            **kwargs: Additional parameters
        """
        self.config = config or {}
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.training_history = {
            'train_loss': [],
            'val_loss': [],
            'epochs': []
        }
        self.is_trained = False
        
        # Update config with kwargs
        self.config.update(kwargs)
        
    @abstractmethod
    def _build_model(self, input_dim: int, output_dim: int = 1) -> nn.Module:
        """
        Build the neural network architecture.
        
        Args:
            input_dim: Number of input features
            output_dim: Number of output predictions (default: 1 for RUL)
            
        Returns:
            PyTorch nn.Module
        """
        pass
    
    @abstractmethod
    def fit(self, X_train: np.ndarray, y_train: np.ndarray, 
            X_val: np.ndarray = None, y_val: np.ndarray = None,
            **kwargs) -> Dict:
        """
        Train the model on training data.
        
        Args:
            X_train: Training features (n_samples, n_features) or (n_samples, seq_len, n_features)
            y_train: Training targets (n_samples,)
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            
        Returns:
            Training history dict with losses
        """
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make RUL predictions.
        
        Args:
            X: Input features (n_samples, n_features) or (n_samples, seq_len, n_features)
            
        Returns:
            Predicted RUL values (n_samples,)
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """
        Save model weights and configuration.
        
        Args:
            path: Directory to save model
        """
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """
        Load model from disk.
        
        Args:
            path: Directory containing saved model
        """
        pass
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            **self.config,
            'model_class': self.__class__.__name__,
            'device': str(self.device),
            'is_trained': self.is_trained
        }
    
    def set_feature_stats(self, mean: np.ndarray, std: np.ndarray):
        """
        Store feature normalization statistics.
        
        Args:
            mean: Feature means (n_features,)
            std: Feature standard deviations (n_features,)
        """
        self.feature_mean = mean
        self.feature_std = std
    
    def normalize_features(self, X: np.ndarray) -> np.ndarray:
        """
        Normalize features using stored statistics.
        
        Args:
            X: Input features
            
        Returns:
            Normalized features
        """
        if not hasattr(self, 'feature_mean') or not hasattr(self, 'feature_std'):
            return X
        return (X - self.feature_mean) / (self.feature_std + 1e-8)
    
    def denormalize_targets(self, y: np.ndarray) -> np.ndarray:
        """
        Denormalize target predictions if targets were normalized.
        
        Args:
            y: Normalized predictions
            
        Returns:
            Denormalized predictions
        """
        if not hasattr(self, 'target_mean') or not hasattr(self, 'target_std'):
            return y
        return y * (self.target_std + 1e-8) + self.target_mean
    
    def count_parameters(self) -> int:
        """Count trainable parameters"""
        if self.model is None:
            return 0
        return sum(p.numel() for p in self.model.parameters() if p.requires_grad)


class LSTMBaseline(BaseRULMethod):
    """
    LSTM-based RUL estimation baseline.
    
    Architecture:
    - LSTM layers (configurable)
    - Fully connected layers
    - Output: RUL prediction
    
    Reference: Simple LSTM baseline for battery RUL estimation
    """
    
    def __init__(self, config: Dict = None, **kwargs):
        """
        Initialize LSTM baseline.
        
        Args:
            config: Dict with hyperparameters:
                - input_dim: Number of input features
                - hidden_dim: LSTM hidden dimension (default: 64)
                - num_layers: Number of LSTM layers (default: 2)
                - dropout: Dropout rate (default: 0.2)
                - learning_rate: Learning rate (default: 0.001)
                - batch_size: Batch size (default: 32)
                - epochs: Number of training epochs (default: 100)
        """
        default_config = {
            'input_dim': 10,
            'hidden_dim': 64,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 100,
            'sequence_length': 50,
        }
        
        super().__init__(default_config, **kwargs)
        if config:
            self.config.update(config)
        
        # Build model
        self.model = self._build_model(
            input_dim=self.config['input_dim'],
            output_dim=1
        ).to(self.device)
        
        print(f"✓ LSTM Baseline initialized on {self.device}")
        print(f"  Parameters: {self.count_parameters():,}")
    
    def _build_model(self, input_dim: int, output_dim: int = 1) -> nn.Module:
        """Build LSTM model"""
        
        class LSTMModel(nn.Module):
            def __init__(self, input_dim, hidden_dim, num_layers, dropout, output_dim):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_dim,
                    hidden_size=hidden_dim,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=dropout if num_layers > 1 else 0
                )
                self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
                self.relu = nn.ReLU()
                self.dropout = nn.Dropout(dropout)
                self.fc2 = nn.Linear(hidden_dim // 2, output_dim)
            
            def forward(self, x):
                # x: (batch, seq_len, input_dim)
                lstm_out, (h_n, c_n) = self.lstm(x)
                # Use last hidden state
                out = h_n[-1]  # (batch, hidden_dim)
                out = self.fc1(out)
                out = self.relu(out)
                out = self.dropout(out)
                out = self.fc2(out)
                return out.squeeze(-1)
        
        return LSTMModel(
            input_dim=input_dim,
            hidden_dim=self.config['hidden_dim'],
            num_layers=self.config['num_layers'],
            dropout=self.config['dropout'],
            output_dim=output_dim
        )
    
    def _create_sequences(self, X: np.ndarray, y: np.ndarray, 
                          seq_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM input.
        
        Args:
            X: Features (n_samples, n_features)
            y: Targets (n_samples,)
            seq_length: Sequence length
            
        Returns:
            X_seq: Sequences (n_sequences, seq_length, n_features)
            y_seq: Targets for each sequence (n_sequences,)
        """
        X_seq, y_seq = [], []
        
        for i in range(len(X) - seq_length):
            X_seq.append(X[i:i + seq_length])
            y_seq.append(y[i + seq_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def fit(self, X_train: np.ndarray, y_train: np.ndarray,
            X_val: np.ndarray = None, y_val: np.ndarray = None,
            **kwargs) -> Dict:
        """
        Train the LSTM model.
        
        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Training targets (n_samples,)
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            
        Returns:
            Training history
        """
        # Override config with kwargs
        epochs = kwargs.get('epochs', self.config['epochs'])
        batch_size = kwargs.get('batch_size', self.config['batch_size'])
        learning_rate = kwargs.get('learning_rate', self.config['learning_rate'])
        seq_length = self.config['sequence_length']
        
        # Store normalization stats
        self.feature_mean = X_train.mean(axis=0)
        self.feature_std = X_train.std(axis=0)
        self.target_mean = y_train.mean()
        self.target_std = y_train.std()
        
        # Normalize
        X_train_norm = self.normalize_features(X_train)
        X_train_seq, y_train_seq = self._create_sequences(X_train_norm, y_train, seq_length)
        
        # Normalize targets
        y_train_seq = (y_train_seq - self.target_mean) / (self.target_std + 1e-8)
        
        if X_val is not None:
            X_val_norm = self.normalize_features(X_val)
            X_val_seq, y_val_seq = self._create_sequences(X_val_norm, y_val, seq_length)
            y_val_seq = (y_val_seq - self.target_mean) / (self.target_std + 1e-8)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train_seq).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train_seq).to(self.device)
        
        if X_val is not None:
            X_val_tensor = torch.FloatTensor(X_val_seq).to(self.device)
            y_val_tensor = torch.FloatTensor(y_val_seq).to(self.device)
        
        # Optimizer and loss
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training loop
        n_batches = len(X_train_tensor) // batch_size
        
        print(f"\n🔋 Training LSTM Baseline")
        print(f"  Train sequences: {len(X_train_seq)}")
        print(f"  Epochs: {epochs}, Batch size: {batch_size}")
        print(f"  Learning rate: {learning_rate}")
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0.0
            
            # Shuffle
            perm = torch.randperm(len(X_train_tensor))
            X_train_tensor = X_train_tensor[perm]
            y_train_tensor = y_train_tensor[perm]
            
            for i in range(n_batches):
                start_idx = i * batch_size
                end_idx = start_idx + batch_size
                
                batch_X = X_train_tensor[start_idx:end_idx]
                batch_y = y_train_tensor[start_idx:end_idx]
                
                optimizer.zero_grad()
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            train_loss /= n_batches
            self.training_history['train_loss'].append(train_loss)
            
            # Validation
            val_loss = None
            if X_val is not None:
                self.model.eval()
                with torch.no_grad():
                    val_predictions = self.model(X_val_tensor)
                    val_loss = criterion(val_predictions, y_val_tensor).item()
                self.training_history['val_loss'].append(val_loss)
            
            self.training_history['epochs'].append(epoch + 1)
            
            # Progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                val_msg = f" | Val Loss: {val_loss:.4f}" if val_loss else ""
                print(f"  Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f}{val_msg}")
        
        self.is_trained = True
        print(f"\n✓ Training complete!")
        
        return self.training_history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make RUL predictions.
        
        Args:
            X: Input features (n_samples, n_features)
            
        Returns:
            Predicted RUL values
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction")
        
        self.model.eval()
        
        # Normalize
        X_norm = self.normalize_features(X)
        
        # Create sequences (use last seq_length samples for each prediction)
        seq_length = self.config['sequence_length']
        predictions = []
        
        for i in range(seq_length, len(X_norm)):
            seq = X_norm[i-seq_length:i]
            seq_tensor = torch.FloatTensor(seq).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                pred = self.model(seq_tensor).cpu().numpy()[0]
            
            # Denormalize
            pred = pred * (self.target_std + 1e-8) + self.target_mean
            predictions.append(pred)
        
        return np.array(predictions)
    
    def save(self, path: str) -> None:
        """Save model"""
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model weights
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': None,  # Can add if needed
            'config': self.config,
            'feature_mean': self.feature_mean if hasattr(self, 'feature_mean') else None,
            'feature_std': self.feature_std if hasattr(self, 'feature_std') else None,
            'target_mean': self.target_mean if hasattr(self, 'target_mean') else None,
            'target_std': self.target_std if hasattr(self, 'target_std') else None,
            'training_history': self.training_history,
        }, save_dir / 'model.pt')
        
        # Save config as JSON
        with open(save_dir / 'config.json', 'w') as f:
            json.dump(self.get_config(), f, indent=2)
        
        print(f"✓ Model saved to {path}")
    
    def load(self, path: str) -> None:
        """Load model"""
        load_dir = Path(path)
        
        checkpoint = torch.load(load_dir / 'model.pt', map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.config = checkpoint['config']
        self.feature_mean = checkpoint['feature_mean']
        self.feature_std = checkpoint['feature_std']
        self.target_mean = checkpoint['target_mean']
        self.target_std = checkpoint['target_std']
        self.training_history = checkpoint['training_history']
        self.is_trained = True
        
        print(f"✓ Model loaded from {path}")


if __name__ == '__main__':
    # Test the template
    print("Testing LSTM Baseline Template...")
    
    # Create dummy data
    np.random.seed(42)
    n_samples = 1000
    n_features = 10
    
    X = np.random.randn(n_samples, n_features).astype(np.float32)
    y = np.random.randn(n_samples).astype(np.float32) * 100 + 500  # RUL values
    
    # Split
    split = int(0.8 * n_samples)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # Create and train model
    model = LSTMBaseline(config={'input_dim': n_features, 'epochs': 20})
    history = model.fit(X_train, y_train, X_test, y_test)
    
    # Predict
    predictions = model.predict(X_test)
    print(f"\nPredictions shape: {predictions.shape}")
    print(f"Prediction range: {predictions.min():.1f} - {predictions.max():.1f}")
    
    # Save and load
    model.save('/tmp/test_lstm_rul')
    
    # Load in new instance
    model2 = LSTMBaseline()
    model2.load('/tmp/test_lstm_rul')
    print("\n✓ Template test passed!")
