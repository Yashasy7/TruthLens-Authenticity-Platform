import cv2
import numpy as np


class FrequencyAnalyzer:
    """
    2D Fast Fourier Transform (FFT) image frequency anomaly analyzer.
    
    Generative architectures (GANs, Diffusion models) often introduce subtle periodic
    artifacts caused by transpose convolutions, pixel-shuffle layers, or spatial upsampling.
    These manifest as anomalous periodic spikes, grid artifacts, or unusual high-frequency
    radial power drop-offs in the 2D Fourier spectrum.
    """

    def analyze_frequency(self, img_rgb: np.ndarray) -> dict:
        """
        Calculates 2D FFT magnitude spectrum and evaluates spectral regularity.
        
        Returns:
            Dictionary with fft_anomaly_score, high_frequency_energy_ratio,
            spectral_kurtosis, and periodic_peak_count.
        """
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape

        # 1. Compute 2D Discrete Fourier Transform and shift low frequencies to center
        dft = np.fft.fft2(gray)
        dft_shift = np.fft.fftshift(dft)
        magnitude_spectrum = np.abs(dft_shift)
        log_spectrum = np.log1p(magnitude_spectrum)

        # 2. Compute radial frequency energy distribution (Low, Mid, High frequency bands)
        cy, cx = h // 2, w // 2
        y, x = np.ogrid[:h, :w]
        distances = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        max_distance = np.sqrt(cx ** 2 + cy ** 2)
        norm_distances = distances / (max_distance + 1e-6)

        low_mask = norm_distances <= 0.25
        high_mask = norm_distances > 0.50

        total_energy = float(np.sum(magnitude_spectrum) + 1e-6)
        low_energy = float(np.sum(magnitude_spectrum[low_mask]))
        high_energy = float(np.sum(magnitude_spectrum[high_mask]))

        high_energy_ratio = high_energy / total_energy

        # 3. Detect anomalous periodic frequency spikes (peaks > mean + 4*std in high-frequency band)
        high_spectrum = log_spectrum[high_mask]
        mean_high = float(np.mean(high_spectrum))
        std_high = float(np.std(high_spectrum))
        threshold = mean_high + 4.0 * std_high
        peak_count = int(np.sum(high_spectrum > threshold))

        # 4. Normalized anomaly score combining spectral peak density and high-energy ratio
        # Natural photographic images follow power-law 1/f decay; generative models often exhibit
        # elevated high-frequency spikes or abnormally flat high-frequency distributions.
        peak_factor = min(1.0, peak_count / 100.0)
        energy_deviation = min(1.0, abs(high_energy_ratio - 0.15) * 4.0)

        anomaly_score = float(np.clip(0.6 * peak_factor + 0.4 * energy_deviation, 0.0, 1.0))

        return {
            "fft_anomaly_score": round(anomaly_score, 4),
            "high_frequency_energy_ratio": round(high_energy_ratio, 4),
            "low_frequency_energy_ratio": round(low_energy / total_energy, 4),
            "spectral_peak_count": peak_count,
            "spectral_mean": round(mean_high, 4),
            "spectral_std": round(std_high, 4)
        }
