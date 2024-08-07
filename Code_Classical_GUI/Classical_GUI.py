from tkinter import *
from tkinter.scrolledtext import ScrolledText
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.pyplot as plt
from ultrasonic_data_extractor import RedPitayaSensor
import time

class EnhancedRedPitayaSensor(RedPitayaSensor):
    def __init__(self):
        super().__init__()
        self.data_storage = []
        self.data_limit = 2

    def get_data_from_server(self):
        while len(self.data_storage) < self.data_limit:
            data = super().get_data_from_server()
            if data is not None:
                self.data_storage.append(data)
                print(f"Data set {len(self.data_storage)} stored.")
            else:
                break
        return self.data_storage

    def reset_data_storage(self):
        self.data_storage = []

def kalman_filter(signal, process_variance=1e-5, measurement_variance=0.5):
    n_iterations = len(signal)
    smoothed_signal = np.zeros(n_iterations)
    error_covariance = 0.0
    current_estimate = signal[0]

    for t in range(n_iterations):
        error_covariance += process_variance
        kalman_gain = error_covariance / (error_covariance + measurement_variance)
        current_estimate += kalman_gain * (signal[t] - current_estimate)
        error_covariance *= (1 - kalman_gain)
        smoothed_signal[t] = current_estimate

    return smoothed_signal

def yanowitz_bruckstein_thresholding(signal, window_size=100, threshold_init_factor=0.5, min_peak_prominence=0.1):
    threshold = threshold_init_factor * np.max(signal)

    for i in range(window_size, len(signal) - window_size):
        window = signal[i - window_size:i + window_size]
        local_max = np.max(window)

        if local_max > threshold:
            threshold = local_max - min_peak_prominence

        if signal[i] >= threshold and signal[i] == local_max:
            if all(signal[i] >= signal[j] for j in range(i - window_size, i + window_size) if j != i):
                return i

    return None

def niblacks_local_thresholding(signal, window_size=2000, k=2.7):
    n = len(signal)
    for i in range(window_size, n - window_size):
        local_segment = signal[i - window_size:i + window_size]
        local_mean = np.mean(local_segment)
        local_std = np.std(local_segment)
        threshold = local_mean + k * local_std

        if signal[i] > threshold:
            if all(signal[i] >= signal[j] for j in range(i - window_size, i + window_size) if j != i):
                return i

    return None

def calculate_distance(peak_index, temperature, sampling_frequency):
    speed_of_sound = 331.45 + 0.606 * temperature
    time_delay = peak_index / sampling_frequency
    distance = 0.5 * speed_of_sound * time_delay
    return distance

def update_parameters_display(method_var, yanowitz_frame, niblack_frame):
    if method_var.get() == 'Yanowitz-Bruckstein Thresholding':
        yanowitz_frame.pack(side=TOP, fill=X)
        niblack_frame.pack_forget()
    elif method_var.get() == 'Niblack\'s Local Thresholding':
        niblack_frame.pack(side=TOP, fill=X)
        yanowitz_frame.pack_forget()

def clear_plot(master):
    for widget in master.pack_slaves():
        if isinstance(widget, Canvas):
            widget.destroy()

def process_and_plot_signal(temperature_var, sampling_frequency_var, peak_detection_method,
                            yanowitz_frame, niblack_frame, master, output_text, selected_signal, sensor):
    clear_plot(master)
    output_text.delete('1.0', END)
    output_text.insert(END, "Starting data processing...\n")
    master.update()

    try:
        temperature = float(temperature_var.get())
        sampling_frequency = int(sampling_frequency_var.get())
    except ValueError:
        output_text.insert(END, "Invalid temperature or sampling frequency. Please enter valid numbers.\n")
        return

    signal_index = int(selected_signal.get().split()[-1]) - 1
    if signal_index >= len(sensor.data_storage):
        output_text.insert(END, f"Selected signal {signal_index + 1} is not available.\n")
        return

    raw_adc = sensor.data_storage[signal_index]
    output_text.insert(END, f"Processing data for signal {signal_index + 1}...\n")
    output_text.insert(END, f"Length of Extracted Ultrasonic Data = {len(raw_adc)}\n")
    master.update()

    filtered_signal = kalman_filter(raw_adc)

    if peak_detection_method.get() == 'Yanowitz-Bruckstein Thresholding':
        peak_index = yanowitz_bruckstein_thresholding(filtered_signal)
    elif peak_detection_method.get() == 'Niblack\'s Local Thresholding':
        peak_index = niblacks_local_thresholding(filtered_signal)

    figure = plt.Figure(figsize=(14, 7), dpi=100)
    ax = figure.add_subplot(111)
    time = np.arange(len(raw_adc))
    ax.plot(time, raw_adc, label='Original Signal', color='lightgray')
    ax.plot(time, filtered_signal, label='Filtered Signal', color='blue')

    if peak_index is not None:
        distance = calculate_distance(peak_index, temperature, sampling_frequency)
        ax.plot(time[peak_index], filtered_signal[peak_index], 'rx', markersize=12, label='Detected Peak')
        output_text.insert(END, f"First peak detected at index: {peak_index}, corresponding to a distance of {distance:.2f} meters\n")
    else:
        output_text.insert(END, "No peak detected.\n")

    ax.set_xlabel('Time')
    ax.set_ylabel('Signal Amplitude')
    ax.legend()

    canvas = FigureCanvasTkAgg(figure, master=master)
    canvas.draw()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
    output_text.insert(END, "Plotting completed.\n")
    master.update()

def extract_data(sensor, output_text):
    output_text.delete('1.0', END)
    output_text.insert(END, "Starting data acquisition...\n")
    sensor.reset_data_storage()
    start_time = time.time()
    sensor.get_data_from_server()
    end_time = time.time()
    output_text.insert(END, "Data acquisition completed.\n")
    output_text.insert(END, f"Data acquisition time: {end_time - start_time:.2f} seconds\n")

def main():
    root = Tk()
    root.title("Classical Tool for ADC signal processing to detect the first peak and measure the distance w.r.t ambient temperature")

    temperature_var = StringVar(value="20")  # Default temperature in Celsius
    sampling_frequency_var = StringVar(value="1953125")  # Default sampling frequency in Hz

    config_frame = Frame(root)
    config_frame.pack(side=TOP, fill=X)

    Label(config_frame, text="Temperature (°C):").pack(side=LEFT)
    Entry(config_frame, textvariable=temperature_var).pack(side=LEFT)

    Label(config_frame, text="Sampling Frequency (Hz):").pack(side=LEFT)
    Entry(config_frame, textvariable=sampling_frequency_var).pack(side=LEFT)

    peak_detection_method = StringVar(value="Yanowitz-Bruckstein Thresholding")

    method_frame = Frame(root)
    method_frame.pack(side=TOP)

    yanowitz_frame = Frame(root)
    niblack_frame = Frame(root)

    # Yanowitz parameters setup
    yanowitz_params = {'window_size': StringVar(value='100'),
                       'threshold_init_factor': StringVar(value='0.5'),
                       'min_peak_prominence': StringVar(value='0.1')}
    for key, var in yanowitz_params.items():
        param_frame = Frame(yanowitz_frame)
        param_frame.pack(side=TOP, fill=X)
        Label(param_frame, text=key.replace('_', ' ').title() + ":").pack(side=LEFT)
        Entry(param_frame, textvariable=var).pack(side=LEFT)

    # Niblack parameters setup
    niblack_params = {'window_size': StringVar(value='2000'),
                      'k': StringVar(value='2.7')}
    for key, var in niblack_params.items():
        param_frame = Frame(niblack_frame)
        param_frame.pack(side=TOP, fill=X)
        Label(param_frame, text=key.replace('_', ' ').title() + ":").pack(side=LEFT)
        Entry(param_frame, textvariable=var).pack(side=LEFT)

    Radiobutton(method_frame, text="Yanowitz-Bruckstein Thresholding", variable=peak_detection_method,
                value="Yanowitz-Bruckstein Thresholding", command=lambda: update_parameters_display(peak_detection_method, yanowitz_frame, niblack_frame)).pack(side=LEFT)
    Radiobutton(method_frame, text="Niblack's Local Thresholding", variable=peak_detection_method,
                value="Niblack's Local Thresholding", command=lambda: update_parameters_display(peak_detection_method, yanowitz_frame, niblack_frame)).pack(side=LEFT)

    signal_var = StringVar(value="Signal 1")
    signal_selection_frame = Frame(root)
    signal_selection_frame.pack(side=TOP, fill=X)

    Radiobutton(signal_selection_frame, text="Signal 1", variable=signal_var, value="Signal 1").pack(side=LEFT)
    Radiobutton(signal_selection_frame, text="Signal 2", variable=signal_var, value="Signal 2").pack(side=LEFT)

    sensor = EnhancedRedPitayaSensor()

    start_button = Button(root, text="Start Data Acquisition", command=lambda: extract_data(sensor, output_text))
    start_button.pack(side=TOP)

    process_button = Button(root, text="Process and Plot Signal", command=lambda: process_and_plot_signal(temperature_var, sampling_frequency_var, peak_detection_method, yanowitz_frame, niblack_frame, root, output_text, signal_var, sensor))
    process_button.pack(side=TOP)

    stop_button = Button(root, text="Stop", command=root.destroy)
    stop_button.pack(side=TOP)

    output_text = ScrolledText(root, height=8)
    output_text.pack(side=BOTTOM, fill=BOTH, expand=True)

    update_parameters_display(peak_detection_method, yanowitz_frame, niblack_frame)  # Initialize parameter display based on default method

    root.mainloop()

if __name__ == "__main__":
    main()
