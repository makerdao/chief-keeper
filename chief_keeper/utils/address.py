# This utility provides an Address class that validates Ethereum addresses and 
# converts them to checksum addresses. The Address class ensures that only valid 
# Ethereum addresses are used and provides methods for comparison and hashing.
#
# Class:
# - Address: Validates and normalizes Ethereum addresses to checksum format.
#
# Methods:
# - is_valid_address: Validates if the provided address is a checksum address.
# - __str__: Returns the checksum address as a string.
# - __eq__: Compares two Address instances for equality.
# - __hash__: Provides a hash value for the Address instance.
#
# Example:
# address = Address('0x32Be343B94f860124dC4fEe278FDCBD38C102D88')
# print(address)  # Outputs the checksum address



from eth_utils import is_checksum_address, to_checksum_address

class Address:
    def __init__(self, address: str):
        if not self.is_valid_address(address):
            raise ValueError(f"Invalid Ethereum address: {address}")
        self.address = to_checksum_address(address)

    @staticmethod
    def is_valid_address(address: str) -> bool:
        return is_checksum_address(address)

    def __str__(self):
        return self.address

    def __eq__(self, other):
        if isinstance(other, Address):
            return self.address == other.address
        return False

    def __hash__(self):
        return hash(self.address)
