"""
ECG Service - ML-based ECG Arrhythmia Detection
Ensemble model using CNN, LSTM, CNN-LSTM, and Random Forest
"""

import os
import sys
import importlib
import pickle
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import Counter
from flask import current_app

# Handle numpy compatibility
try:
    if 'numpy._core' not in sys.modules:
        sys.modules['numpy._core'] = importlib.import_module('numpy.core')
        sys.modules['numpy._core._multiarray_umath'] = importlib.import_module('numpy.core._multiarray_umath')
except:
    pass

# Try to import TensorFlow
try:
    from tensorflow import keras
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("⚠️ TensorFlow not installed. ECG detection will be limited.")

# Try to import scipy
try:
    from scipy.signal import butter, filtfilt, find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ SciPy not installed. ECG processing will be limited.")


class ECGProcessor:
    """Process ECG signals - filtering and beat detection"""
    
    def __init__(self, fs=360):
        self.fs = fs  # Sampling frequency (MIT-BIH uses 360 Hz)
    
    def butter_bandpass_filter(self, data, lowcut=0.5, highcut=40, order=5):
        """Bandpass filter for ECG signal"""
        if not SCIPY_AVAILABLE:
            return data
        
        nyq = 0.5 * self.fs
        low = lowcut / nyq
        high = highcut / nyq
        low = max(0.01, min(low, 0.99))
        high = max(0.01, min(high, 0.99))
        
        b, a = butter(order, [low, high], btype='band')
        padlen = min(len(data) - 1, 3 * max(len(a), len(b)))
        
        if len(data) > padlen:
            y = filtfilt(b, a, data, padlen=padlen)
        else:
            y = filtfilt(b, a, data)
        
        return y
    
    def process_signal(self, signal):
        """
        Process ECG signal - normalize, filter, detect R-peaks
        
        Returns:
            beat_windows: List of 180-sample beat windows
            valid_peaks: List of R-peak positions
            filtered_signal: Filtered ECG signal
        """
        if not SCIPY_AVAILABLE:
            return [], [], signal
        
        # Normalize signal
        signal_normalized = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
        
        # Apply bandpass filter
        signal_filtered = self.butter_bandpass_filter(signal_normalized)
        
        # R-peak detection with optimized parameters
        peaks, properties = find_peaks(
            signal_filtered,
            distance=int(0.35 * self.fs),  # 0.35 sec minimum between peaks
            prominence=0.2,                 # Minimum prominence
            height=0.1,                     # Minimum height
            width=3                         # Minimum width
        )
        
        print(f"🔍 R-peak detection: Found {len(peaks)} peaks in {len(signal)} samples")
        
        # Extract beat windows (90 samples before and after R-peak)
        beat_windows = []
        valid_peaks = []
        
        for peak in peaks:
            if peak < 90 or peak > len(signal_filtered) - 90:
                continue
            
            segment = signal_filtered[peak-90:peak+90]
            
            if len(segment) == 180:
                segment_norm = (segment - np.mean(segment)) / (np.std(segment) + 1e-8)
                beat_windows.append(segment_norm)
                valid_peaks.append(peak)
        
        print(f"✅ Valid beats extracted: {len(beat_windows)}")
        
        return beat_windows, valid_peaks, signal_filtered


class ECGEnsemble:
    """Ensemble model for ECG classification"""
    
    def __init__(self, models, scaler, label_encoder):
        self.models = models
        self.scaler = scaler
        self.label_encoder = label_encoder
        
        # Model weights for ensemble voting
        self.model_weights = {
            'cnn': 0.10,
            'cnn_lstm': 0.25,
            'random_forest': 0.20,
            'lstm': 0.45
        }
    
    def _apply_temperature(self, logits, temperature):
        """Apply temperature scaling to soften probabilities"""
        if logits.ndim == 1:
            logits = logits.reshape(1, -1)
        
        scaled_logits = logits / temperature
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits, axis=1, keepdims=True))
        return exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
    
    def predict_single_beat(self, beat_window):
        """
        Predict class for a single heartbeat
        
        Returns:
            class_name: Predicted class (N, V, S, F, Q)
            confidence: Confidence score
        """
        # Normalize beat
        beat_normalized = self.scaler.transform(beat_window.reshape(1, -1))
        
        weighted_probs = None
        
        # Temperature scaling for calibration
        temperature_cnn = 1.2
        temperature_others = 1.1
        
        for model_name, weight in self.model_weights.items():
            model = self.models.get(model_name)
            if model is None:
                continue
            
            if isinstance(model, keras.Model):
                X_dl = beat_normalized.reshape(1, 180, 1)
                pred_logits = model.predict(X_dl, verbose=0)
                
                if model_name == 'cnn':
                    pred_probs = self._apply_temperature(pred_logits, temperature_cnn)
                else:
                    pred_probs = self._apply_temperature(pred_logits, temperature_others)
            else:
                # Random Forest
                pred_probs = model.predict_proba(beat_normalized)
            
            if weighted_probs is None:
                weighted_probs = weight * pred_probs
            else:
                weighted_probs += weight * pred_probs
        
        pred_class = np.argmax(weighted_probs, axis=1)[0]
        confidence = np.max(weighted_probs, axis=1)[0]
        
        class_name = self.label_encoder.inverse_transform([pred_class])[0]
        
        # Fusion beat threshold - require higher confidence
        if class_name == 'F' and confidence < 0.55:
            sorted_indices = np.argsort(weighted_probs[0])[::-1]
            second_best_idx = sorted_indices[1]
            second_best_class = self.label_encoder.inverse_transform([second_best_idx])[0]
            second_best_conf = weighted_probs[0][second_best_idx]
            
            if second_best_class != 'F' and second_best_conf > 0.35:
                class_name = second_best_class
                confidence = second_best_conf
        
        # Low confidence = Unknown
        if confidence < 0.20:
            class_name = 'Q'
        
        return class_name, confidence


class ECGService:
    """Main ECG Analysis Service"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
        
        self.model_path = None
        self.ensemble = None
        self.processor = None
        self.scaler = None
        self.label_encoder = None
        self.models_loaded = False
        self.initialized = True
    
    def init_app(self, app):
        """Initialize with Flask app"""
        # Get model path from config or use default
        self.model_path = app.config.get('ECG_MODEL_PATH', 
                                         os.path.join(app.static_folder, 'models', 'ecg'))
        
        # Try to load models
        try:
            self.load_models()
        except Exception as e:
            print(f"⚠️ ECG models not loaded: {e}")
    
    def load_models(self):
        """Load all ECG models"""
        if self.models_loaded:
            return True
        
        if not TENSORFLOW_AVAILABLE:
            print("❌ TensorFlow required for ECG detection")
            return False
        
        if not self.model_path or not os.path.exists(self.model_path):
            print(f"❌ ECG model path not found: {self.model_path}")
            return False
        
        try:
            print(f"📂 Loading ECG models from: {self.model_path}")
            
            # Load scaler
            scaler_path = os.path.join(self.model_path, 'scaler.pkl')
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print("  ✅ Scaler loaded")
            
            # Load label encoder
            encoder_path = os.path.join(self.model_path, 'label_encoder.pkl')
            with open(encoder_path, 'rb') as f:
                self.label_encoder = pickle.load(f)
            print("  ✅ Label encoder loaded")
            
            # Load Random Forest
            rf_path = os.path.join(self.model_path, 'random_forest.pkl')
            with open(rf_path, 'rb') as f:
                rf_model = pickle.load(f)
            print("  ✅ Random Forest loaded")
            
            # Load Deep Learning models
            cnn_model = keras.models.load_model(
                os.path.join(self.model_path, 'cnn_model.h5'),
                compile=False
            )
            print("  ✅ CNN model loaded")
            
            lstm_model = keras.models.load_model(
                os.path.join(self.model_path, 'lstm_model.h5'),
                compile=False
            )
            print("  ✅ LSTM model loaded")
            
            cnn_lstm_model = keras.models.load_model(
                os.path.join(self.model_path, 'cnn_lstm_model.h5'),
                compile=False
            )
            print("  ✅ CNN-LSTM model loaded")
            
            # Create ensemble
            self.ensemble = ECGEnsemble(
                {
                    'random_forest': rf_model,
                    'cnn': cnn_model,
                    'lstm': lstm_model,
                    'cnn_lstm': cnn_lstm_model
                },
                self.scaler,
                self.label_encoder
            )
            
            # Create processor
            self.processor = ECGProcessor(fs=360)
            
            self.models_loaded = True
            print("✅ All ECG models loaded successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error loading ECG models: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def read_ecg_file(self, filepath: str) -> np.ndarray:
        """Read ECG file in various formats"""
        print(f"📂 Reading ECG file: {filepath}")
        
        # Method 1: CSV with voltage in second column
        try:
            data = np.loadtxt(filepath, delimiter=',', skiprows=1, usecols=(1), max_rows=100000)
            if len(data) > 360:
                print(f"  ✅ CSV voltage column: {len(data)} samples")
                return data
        except:
            pass
        
        # Method 2: Single column
        try:
            data = np.loadtxt(filepath, delimiter=',', ndmin=1, max_rows=100000)
            if len(data) > 360:
                print(f"  ✅ Single column: {len(data)} samples")
                return data
        except:
            pass
        
        # Method 3: Space-separated
        try:
            data = np.loadtxt(filepath, usecols=(1), max_rows=100000)
            if len(data) > 360:
                print(f"  ✅ Space-separated: {len(data)} samples")
                return data
        except:
            pass
        
        # Method 4: Take last column
        try:
            full_data = np.loadtxt(filepath, delimiter=',', max_rows=100000)
            if full_data.ndim == 2:
                data = full_data[:, -1]
            else:
                data = full_data
            
            if len(data) > 360:
                print(f"  ✅ Last column: {len(data)} samples")
                return data
        except:
            pass
        
        print("❌ Failed to read ECG file")
        return np.array([])
    
    def analyze_ecg(self, ecg_data: np.ndarray, max_beats: int = 50) -> Dict:
        """
        Analyze ECG data and return predictions
        
        Args:
            ecg_data: ECG signal array
            max_beats: Maximum beats to analyze
            
        Returns:
            Analysis results dictionary
        """
        if not self.models_loaded:
            return {
                'success': False,
                'error': 'ECG models not loaded'
            }
        
        if len(ecg_data) < 360:
            return {
                'success': False,
                'error': f'ECG too short: {len(ecg_data)} samples (need at least 360)'
            }
        
        # Limit analysis to 20 seconds (7200 samples at 360 Hz)
        analysis_samples = min(len(ecg_data), 7200)
        limited_data = ecg_data[:analysis_samples]
        
        print(f"📊 Analyzing {analysis_samples} samples ({analysis_samples/360:.1f} seconds)")
        
        # Process signal
        beat_windows, peaks, filtered_signal = self.processor.process_signal(limited_data)
        
        if len(beat_windows) == 0:
            return {
                'success': False,
                'error': 'No heartbeats detected',
                'waveform_data': limited_data[::10].tolist()
            }
        
        # Classify beats
        predictions = []
        beats_to_analyze = min(max_beats, len(beat_windows))
        
        print(f"🔬 Classifying {beats_to_analyze} beats...")
        
        for i, beat_window in enumerate(beat_windows[:beats_to_analyze]):
            class_name, confidence = self.ensemble.predict_single_beat(beat_window)
            predictions.append({
                'beat_number': i + 1,
                'class': class_name,
                'confidence': float(confidence)
            })
        
        # Calculate statistics
        class_counts = Counter([p['class'] for p in predictions])
        total_beats = len(predictions)
        
        # Calculate percentages
        n_pct = (class_counts.get('N', 0) / total_beats) * 100
        v_pct = (class_counts.get('V', 0) / total_beats) * 100
        s_pct = (class_counts.get('S', 0) / total_beats) * 100
        f_pct = (class_counts.get('F', 0) / total_beats) * 100
        q_pct = (class_counts.get('Q', 0) / total_beats) * 100
        
        # Risk assessment
        if v_pct > 30:
            risk_level = 'HIGH'
            message = '⚠️ High risk: Frequent ventricular ectopy'
        elif f_pct > 50:
            risk_level = 'HIGH'
            message = '⚠️ High risk: Excessive fusion beats detected'
        elif v_pct > 15 or (v_pct + f_pct) > 25:
            risk_level = 'MODERATE'
            message = '⚠️ Moderate risk: Significant abnormal beats'
        elif s_pct > 20:
            risk_level = 'MODERATE'
            message = '⚠️ Moderate risk: Frequent supraventricular beats'
        elif v_pct > 5 or s_pct > 5 or f_pct > 10:
            risk_level = 'LOW'
            message = 'ℹ️ Low risk: Occasional ectopic beats'
        elif q_pct > 30:
            risk_level = 'UNKNOWN'
            message = '❓ Signal quality poor - review recommended'
        elif n_pct >= 85:
            risk_level = 'NORMAL'
            message = '✅ Normal sinus rhythm'
        else:
            risk_level = 'MODERATE'
            message = '⚠️ Review recommended: Mixed rhythm pattern'
        
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        
        print(f"\n📊 Results: {risk_level}")
        print(f"   N: {class_counts.get('N', 0)} ({n_pct:.1f}%)")
        print(f"   V: {class_counts.get('V', 0)} ({v_pct:.1f}%)")
        print(f"   S: {class_counts.get('S', 0)} ({s_pct:.1f}%)")
        print(f"   F: {class_counts.get('F', 0)} ({f_pct:.1f}%)")
        print(f"   Q: {class_counts.get('Q', 0)} ({q_pct:.1f}%)")
        print(f"   Confidence: {avg_confidence:.1%}")
        
        return {
            'success': True,
            'predictions': predictions,
            'statistics': {
                'total_beats': total_beats,
                'total_peaks_detected': len(beat_windows),
                'class_distribution': dict(class_counts),
                'percentages': {
                    'N': round(n_pct, 1),
                    'V': round(v_pct, 1),
                    'S': round(s_pct, 1),
                    'F': round(f_pct, 1),
                    'Q': round(q_pct, 1)
                },
                'analyzed_samples': len(limited_data),
                'sampling_rate': 360,
                'duration_seconds': len(limited_data) / 360
            },
            'risk_level': risk_level,
            'message': message,
            'confidence': avg_confidence,
            'waveform_data': limited_data[::10].tolist()  # Downsampled for visualization
        }


# Singleton instance
ecg_service = ECGService()