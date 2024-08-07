import socket
import struct
import pandas as pd
import threading

class RedPitayaSensor:
    def __init__(self):
        self.buffer_size = 65536
        self.size_of_raw_adc = 16384
        self.msg_from_client = "-a 1"
        self.bytes_to_send = str.encode(self.msg_from_client)
        self.server_address_port = ("192.168.128.1", 61231)
        self.sensor_status_message = "Waiting to Connect with RedPitaya UDP Server!"
        print(self.sensor_status_message)
        self.udp_client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_client_socket.settimeout(10)  # Set timeout for socket operations
        self.send_msg_to_server()
        self.running = True
        self.thread = threading.Thread(target=self.receive_data_loop)
        self.thread.start()

    def get_sensor_status_message(self):
        return self.sensor_status_message

    def send_msg_to_server(self):
        try:
            self.udp_client_socket.sendto(self.bytes_to_send, self.server_address_port)
        except socket.error as e:
            self.sensor_status_message = f"Failed to send message: {e}"
            print(self.sensor_status_message)

    def get_data_from_server(self):
        try:
            packet = self.udp_client_socket.recv(self.buffer_size)
        except socket.timeout:
            self.sensor_status_message = "Connection timed out."
            print(self.sensor_status_message)
            return None
        except socket.error as e:
            self.sensor_status_message = f"Error receiving data: {e}"
            print(self.sensor_status_message)
            return None

        try:
            header_length = int(struct.unpack('@f', packet[:4])[0])
            ultrasonic_data_length = int(struct.unpack('@f', packet[4:8])[0])
            header_data = [i[0] for i in struct.iter_unpack('@f', packet[:header_length])]
            ultrasonic_data = [i[0] for i in struct.iter_unpack('@h', packet[header_length:])]
        except struct.error as e:
            self.sensor_status_message = f"Data unpacking error: {e}"
            print(self.sensor_status_message)
            return None

        self.sensor_status_message = f"Sensor Connected Successfully at {self.server_address_port}!"
        print(self.sensor_status_message)
        print(f"Total Received: {len(packet)} Bytes.")
        print(f"Length of Header: {len(header_data)}")
        print(f"Length of Ultrasonic Data: {len(ultrasonic_data)}")

        df = pd.DataFrame(ultrasonic_data, columns=['raw_adc'])
        return df["raw_adc"]

    def receive_data_loop(self):
        while self.running:
            data = self.get_data_from_server()
            if data is not None:
                print(f"Received Data: {data.head()}")

    def stop(self):
        self.running = False
        self.thread.join()
        self.udp_client_socket.close()

