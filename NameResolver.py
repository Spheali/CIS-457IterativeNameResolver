from dnslib import DNSRecord, DNSHeader, DNSBuffer, DNSQuestion, RR, QTYPE, RCODE
from socket import socket, SOCK_DGRAM, AF_INET

"""
There are 13 root servers defined at https://www.iana.org/domains/root/servers
"""

ROOT_SERVER = "199.7.83.42"    # ICANN Root Server
DNS_PORT = 53
def get_dns_record(udp_socket, domain:str, parent_server: str, record_type):
  q = DNSRecord.question(domain, qtype = record_type)
  q.header.rd = 0   # Recursion Desired?  NO
  print("DNS query", repr(q))
  udp_socket.sendto(q.pack(), (parent_server, DNS_PORT))
  pkt, _ = udp_socket.recvfrom(8192)
  buff = DNSBuffer(pkt)
  
  """
  RFC1035 Section 4.1 Format
  
  The top level format of DNS message is divided into five sections:
  1. Header
  2. Question
  3. Answer
  4. Authority
  5. Additional
  """
  
  header = DNSHeader.parse(buff)
  print("DNS header", repr(header))
  if q.header.id != header.id:
    print("Unmatched transaction")
    return
  if header.rcode != RCODE.NOERROR:
    print("Query failed")
    return

  # Parse the question section #2
  for k in range(header.q):
    q = DNSQuestion.parse(buff)
    print(f"Question-{k} {repr(q)}")
    
  # Parse the answer section #3
  for k in range(header.a):
    a = RR.parse(buff)
    print(f"Answer-{k} {repr(a)}")
    if a.rtype == QTYPE.A:
      print("IP address")
    return([a.rtype,a.rdata])
      
  # Parse the authority section #4
  for k in range(header.auth):
    auth = RR.parse(buff)
    print(f"Authority-{k} {repr(auth)}")
    return([auth.rtype,auth.rdata])
      
  # Parse the additional section #5
  for k in range(header.ar):
    adr = RR.parse(buff)
    print(f"Additional-{k} {repr(adr)} Name: {adr.rname}")
    return ([adr.rtype,adr.rdata])

# When the get_dns_record returns the rtype, it is an int type
# this function translates that int type to a string
def int_to_type(record_type):
  print(record_type, type(record_type))
  if(record_type == 1):
    print("A type")
    return "A"
  elif(record_type == 2):
    print("NS type")
    return "NS"
  elif(record_type == 5):
    print("CNAME type")
    return "CNAME"
  elif(record_type == 28):
    print("AAAA TYPE")
    return "AAAA"
  else:
    print("Not a record type we care about. Defaulting to NS")
    return "NS"

def iterate(udp_socket):
  user = ""
  rec_type = "NS"
  server = ROOT_SERVER

  print("Enter the URL you want to search for: ")
  user = input()
  while(not user == ".exit"):
    # This while loop will keep going until the break condition is met
    # Break condition is the rec_type being A
    while(True):
      # reset server in case "CNAME" type is given
      server = ROOT_SERVER
      URL = user.split('.')
      temp = ""
      rec_type = "NS"

      for x in range(len(URL)):
        # search for record type A when getting to the last server
        # also set the temp variable to be the user input for efficiency
        # if just starting, define temp as the very end of the URL
        # else the temp variable will append to the next part of the URL
        if(x == len(URL)-1):
          rec_type = "A"
          temp = user
        elif(x == 0):
          temp = URL[len(URL)-1]
        else:
          temp = URL[len(URL)-x-1] + "." + temp

        ls = get_dns_record(udp_socket, temp, server, rec_type)
        rec_type = ls[0] # set rec_type to the returned record type
        server = str(ls[1]) # set server to the returned server

        rec_type = int_to_type(rec_type)
                
            # check the record type is CNAME and NS or not
            # if NS, while loop until type A record or CNAME is found
            # if CNAME, change user and URL then continue
            # else, we can break out of the while loop and return the IP address
      if(rec_type == "NS"):
        while(rec_type == "NS"):
          rec_type = "A"
          ls = get_dns_record(udp_socket, temp, server, rec_type)
          rec_type = ls[0]
          server = str(ls[1])
          rec_type = int_to_type(rec_type)
      if(rec_type == "CNAME"):
        user = server
        continue
      else:
        print("IP is",server)
        break
        
        # Ask for the next URL from the user
    print("Enter the URL you want to search for: ")
    user = input()

if __name__ == '__main__':
  # Create a UDP socket
  sock = socket(AF_INET, SOCK_DGRAM)
  
  iterate(sock)

  sock.close()