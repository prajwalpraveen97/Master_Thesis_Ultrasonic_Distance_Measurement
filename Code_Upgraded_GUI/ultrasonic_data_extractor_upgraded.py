import socket, struct
import pandas as pd
import time
import paramiko

class RedPitayaSensor:
    def __init__(self):
        self.size_of_raw_adc = 25000
        self.buffer_size = (self.size_of_raw_adc + 5) * 4
        self.msg_from_client = "-i 1"
        self.hostIP = "192.168.128.1"
        self.data_port = 61231
        self.ssh_port = 22
        self.server_address_port = (self.hostIP, self.data_port)
        # Create a UDP socket at client side
        self.sensor_status_message = "Waiting to Connect with RedPitaya UDP Server!"
        print(self.sensor_status_message)
        self.udp_client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def give_ssh_command(self, command):
        try:
            # Connect to the Redpitaya device
            self.client.connect(self.hostIP, self.ssh_port, "root", "root")
            self.set_sensor_message(f"Connected to Redpitaya {self.hostIP}")

            # Execute the command
            stdin, stdout, stderr = self.client.exec_command(command)

            # Read the command
            output = stdout.read().decode()
            error = stderr.read().decode()

            # Print the output and error (if any)
            self.set_sensor_message(f"Output: {output}")

            if error:
                self.set_sensor_message(f"Error: {error}")

            if output:
                return output

        finally:
            # Close the SSH connection
            self.client.close()
            self.set_sensor_message("Connection closed")

    def set_sensor_message(self, message):
        self.msg_from_client = message

    def get_sensor_status_message(self):
        return self.sensor_status_message

    def send_msg_to_server(self):
        bytes_to_send = str.encode(self.msg_from_client)
        print("Sending message")
        self.udp_client_socket.sendto(bytes_to_send, self.server_address_port)

    def get_data_from_server(self):
        self.msg_from_client = "-i 1"
        self.send_msg_to_server()
        packet = self.udp_client_socket.recv(self.buffer_size)
        self.sensor_status_message = f"Sensor Connected Successfully at {self.server_address_port}!"
        print(self.sensor_status_message)
        print(f"Total Received : {len(packet)} Bytes.")
        header_length = int(struct.unpack('@f', packet[:4])[0])

        self.total_data_blocks = int(struct.unpack('@f', packet[8:12])[0])

        header_data = []
        for i in struct.iter_unpack('@f', packet[:header_length]):
            header_data.append(i[0])

        ultrasonic_data = []
        for i in range(self.total_data_blocks):
            time.sleep(1 / 100)
            self.msg_from_client = "-a 1"
            self.send_msg_to_server()
            packet1 = self.udp_client_socket.recv(self.buffer_size)
            current_data_block_number = int(struct.unpack('@f', packet1[12:16])[0])
            self.sensor_status_message = f"{current_data_block_number + 1} numbered block Successfully received at {self.server_address_port}!"
            ultrasonic_data_length = int(struct.unpack('@f', packet1[4:8])[0])
            for i in struct.iter_unpack('@h', packet1[header_length:]):
                ultrasonic_data.append(i[0])

        print(f"Length of Header : {len(header_data)}")
        print(f"Length of Ultrasonic Data : {len(ultrasonic_data)}")

        df = pd.DataFrame(ultrasonic_data, columns=['raw_adc'])

        return df['raw_adc']