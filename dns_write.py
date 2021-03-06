""" DNS WRITE """
#from fnctl import flock, LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN
import os
import re
import datetime
import base
from mydns import sign_and_compile as mydns_sign_and_compile
from fcntl import flock, LOCK_EX


# DNS_MASTER_ZONE_PATH='/var/named/master'
# DNS_COMPILED_ZONE_PATH='/var/named/master-compiled'

DNS_MASTER_ZONE_PATH='master'
DNS_COMPILED_ZONE_PATH='master-compiled'


#Main functions
def dns_apply_challenge(cn, validation_data):
	base_domain = extract_base_domain(cn)
	zonefile = DNS_MASTER_ZONE_PATH + "/" + base_domain
	zonefile_compiled = DNS_COMPILED_ZONE_PATH + "/" + base_domain


	if base_domain not in os.listdir(DNS_MASTER_ZONE_PATH):
		print zonefile
		return ["Zonefile not found", False]


	#Check if there are any old records. If so, remove them.
	if dns_challenge_in_file(zonefile):
		dns_remove_challenge(cn, False)

	#Write challenges to zonefile
	dns_recs = []
	for data in validation_data:
		dns_recs.append('%s\t60\tIN\tTXT\t"%s"\n' % (data[1].rsplit(".",2)[:-2][0], data[0]))
	zonefile_append = open(zonefile, "a+")
	flock(zonefile_append,LOCK_EX)
	for dns_rec in dns_recs:
		zonefile_append.write(dns_rec)
	zonefile_append.close()
	#Check if we really have chalres in zonefile
	if dns_challenge_in_file(zonefile):
		return dns_compile_zonefile(base_domain, zonefile, zonefile_compiled)
	else:
		return ["Unable to write challenge", False]
def dns_remove_challenge(cn, commit = True):
	base_domain = extract_base_domain(cn)
	zonefile = DNS_MASTER_ZONE_PATH + "/" + base_domain
	zonefile_compiled = DNS_COMPILED_ZONE_PATH + "/" + base_domain

	if base_domain not in os.listdir(DNS_MASTER_ZONE_PATH):
		return ["Zonefile not found", False]

	zonefile_file = open(zonefile, "r+")
	flock(zonefile_file,LOCK_EX)
	with zonefile_file:
		zonefile_read = zonefile_file.readlines()
		zonefile_file.seek(0)
		for line in zonefile_read:
			if "_acme-challenge" not in line:
				zonefile_file.write(line)
		zonefile_file.truncate()
	if dns_challenge_in_file(zonefile):
		print "Something is wrong, cannot remove challenge"
		return False

	#If commit variable is False, do not compile&commit to bind. Just remove records from fileself.
	#Designed for removing residual challenges before trying new
	if not commit:
		return True
	else:
		return dns_compile_zonefile(base_domain, zonefile, zonefile_compiled)


#Subfunctions
def extract_base_domain(cn):
	#Just removing everything except top and second level domains (eg. new.docs.hosting90.cz => hosting90.cz)
	nsfile = cn.split(".")[-2:]
	base_domain = nsfile[0] + "." + nsfile[1]
	return base_domain
def dns_challenge_in_file(zonefile):
	list = []
	for line in open(zonefile, "r"):
		if "_acme-challenge" in line:
			list.append(line)
	if list:
		return True
		#return list
	else:
		return False
def dns_detect_dnssec(zonefile_compiled):
	if 'DNSKEY' in open(zonefile_compiled).read():
		return True
	else:
		return False
def dns_compile_zonefile(base_domain, zonefile, zonefile_compiled):

	####
	return True
	####

	if dns_detect_dnssec(zonefile_compiled):
	#If there are DNSSEC records in zonefile, use prepared function
		compile_result = mydns_sign_and_compile(base_domain, zonefile, zonefile_compiled, True)
		#return dnssec_write

	else:
		#If no dnssec is used, just increase serial and compile zone.
		increment_serial = True
		serial_updated = False
		line = None
		srcfh = open(zonefile,'r+')
		flock(srcfh,LOCK_EX)
		while line == None or line != '':
			line = srcfh.readline()
			if increment_serial and not serial_updated:
				mymatch = re.match('^(\s+([0-9]{10})\s*;\s*serial\s*)$',line)
				if mymatch != None:
					old_serial = int(mymatch.group(2))
					today_serial = int(datetime.date.today().strftime('%Y%m%d00'))
					new_serial = max(old_serial,today_serial)+1
					line = line.replace(mymatch.group(2),str(new_serial))
					filepos = srcfh.tell()
					srcfh.seek(filepos-len(line))
					srcfh.write(line)
					serial_updated=True
		srcfh.close()
		#Compile zone
		(out, err, res) = base.shell_exec2('named-compilezone -o '+zonefile_compiled+' '+ base_domain +' '+zonefile)
		compile_result = res == 0

	os.utime(zonefile_compiled, None)


	if compile_result == True:
		base.shell_exec('rndc reload '+base_domain)
		return [True, "ok" ]
	else:
		return [True, "Zone not loaded:\n"+str(out)+"\n\n"+str(err)]

#debug run
#dns_compile_zonefile("divecky.com", "master/divecky.com", "master-compiled/divecky.com")
