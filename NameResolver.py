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
    #print(f"Question-{k} {repr(q)}")
    
  # Parse the answer section #3
  for k in range(header.a):
    a = RR.parse(buff)
    # # skip answer if it is not the same type as we are looking for (NS, A, AAAA, CNAME)
    # if(int_to_type(a.rtype) == 0):
    #   continue
    #print(f"Answer-{k} {repr(a)}")
    return([a.rtype,a.rdata])
      
  # Parse the authority section #4
  for k in range(header.auth):
    auth = RR.parse(buff)
    #print(f"Authority-{k} {repr(auth)}")
    return([auth.rtype,auth.rdata])
      
  # Parse the additional section #5
  for k in range(header.ar):
    adr = RR.parse(buff)
    #print(f"Additional-{k} {repr(adr)} Name: {adr.rname}")
    return ([adr.rtype,adr.rdata])

# When the get_dns_record returns the rtype, it is an int type
# this function translates that int type to a string
def int_to_type(record_type):
  print(record_type, type(record_type))
  if(record_type == 1):
    return "A"
  elif(record_type == 2):
    return "NS"
  elif(record_type == 5):
    return "CNAME"
  elif(record_type == 28):
    return "AAAA"
  # Default to 0
  else:
    return 0

# Cache that stores all searched for domains, their ip/server as well as what type of question was given
cache = []

# loops through the cache and searches for the specific domain and string 
def check_cache(domain:str):
  # return 0 if cache is empty
  if(len(cache) == 0):
    return(0)
  
  for x in cache[::-1]:
    if(x[0] == domain):
      return([x[1],x[2]])
  
  # return 0 if cache does not contain the domain
  return(0)

def iterate(udp_socket):
  user = ""
  rec_type = "NS"
  server = ROOT_SERVER
  cached = False
  exists = True

  print("Enter the URL you want to search for: ")
  user = input()
  while(not user == ".exit"):
    # This while loop will keep going until the break condition is met
    # Break condition is the rec_type being A
    while(True):

      # User commands
      # Print a list 
      if(user == ".list"):
        if(len(cache) == 0):
          print("Cache is empty")
        for x in range(len(cache)):
          print(x+1, ":", cache[x])
        break

      # Clear the cache
      if(user == ".clear"):
        if(len(cache) == 0):
          print("Cache is empty")
        cache.clear()
        break

      command = user.split(" ")
      # Remove specific index of cache
      if(command[0] == ".remove"):
        if(len(cache) == 0):
          print("Cache is empty")
          break
        # print error message if no index is given
        if(len(command) == 1):
          print("Include what index you want to remove.")
          break
        command[1] = int(command[1])
        # print error message if index is not within len(cache)
        if(command[1] <= 0 or command[1] > len(cache)):
          print("Please choose a index within the length of cache.  Refer to .list for indices")
          break
        print("Removing", cache[command[1]-1])
        cache.pop(command[1]-1)
        break        

      # reset server in case "CNAME" type is given
      server = ROOT_SERVER
      URL = user.split('.')
      temp = ""
      rec_type = "NS"
      cached = False
      exists = True

      # Check cache going backwards from the whole URL to just the low level domain
      for x in range(len(URL)):
        if(x == 0):
          temp = user
        else:
          temp = ".".join(URL[x:])
        
        ls = check_cache(temp)
        
        if(ls == 0):
          continue

        rec_type = ls[1]
        server = ls[0]
      
        print("Got", server, "from cache for the domain", temp)
        cached = True
        break
        
        
      # Need to add a line to add to the cache before looping again
      for x in range(len(URL)):

        # break out of for loop if the A type IP was got from the cache
        if(cached and (rec_type == "A" or rec_type == "CNAME")):
          break
        # continue through loop if not at the correct cached iteration
        if(cached and (len(".".join(URL[len(URL)-x-1:])) <= len(temp))):
          continue

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
        
        # end iteration if negative is given
        if(ls is None):
          print("This URL does not exist")
          exists = False
          break

        old_server = server

        rec_type = ls[0] # set rec_type to the returned record type
        server = str(ls[1]) # set server to the returned server
        rec_type = int_to_type(rec_type)

        cache.append(tuple([temp, server, rec_type]))
        if(temp != user):
          print("Got", server, "from DNS query to TLD server", old_server, "for domain", temp, ".  Caching...")
        else:
          print("Got", server, "from DNS query to Authoritative server", old_server, "for domain", temp, ".  Caching...")
                
      # check the record type is CNAME and NS or not
      # if NS, while loop until type A record or CNAME is found
      # if CNAME, change user and URL then continue
      # else, we can break out of the while loop and return the IP address
      # also if we couldn't find the server earlier then we just break out
      if(rec_type == "NS" and exists):
        while(rec_type == "NS"):
          rec_type = "A"
          ls = get_dns_record(udp_socket, temp, server, rec_type)

          if(ls == 0):
            print("This URL does not exist")
            exists = False
            break

          old_server = server
          rec_type = ls[0]
          server = str(ls[1])
          rec_type = int_to_type(rec_type)
          cache.append(tuple([temp, server, rec_type]))
          print("Got", server, "from DNS query to Authoritative server", old_server, "for domain", temp, ".  Caching...")

      if(rec_type == "CNAME" and exists):
        user = server
        continue

      elif(exists):
        print("IP is",server)
        break

      else:
        break
        
        # Ask for the next URL from the user
    print("Enter the URL you want to search for: ")
    user = input()

if __name__ == '__main__':
  # Create a UDP socket
  sock = socket(AF_INET, SOCK_DGRAM)
  
  iterate(sock)

  sock.close()