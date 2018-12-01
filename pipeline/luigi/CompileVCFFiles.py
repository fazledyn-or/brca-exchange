import subprocess
import os
import urllib2
import tarfile
import datetime
import socket
from shutil import copy
import luigi
import csv
from luigi.util import inherits, requires
import re
import tempfile
import shutil
import json

from retrying import retry


#######################
# Convenience methods #
#######################


def create_path_if_nonexistent(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def print_subprocess_output_and_error(sp):
    out, err = sp.communicate()
    if out:
        print "standard output of subprocess:"
        print out
    if err:
        print "standard error of subprocess:"
        print err


@retry(stop_max_attempt_number=3, wait_fixed=3000)
def urlopen_with_retry(url):
    return urllib2.urlopen(url)


def download_file_and_display_progress(url, file_name=None):
    if file_name is None:
        file_name = url.split('/')[-1]

    u = urlopen_with_retry(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()
    print "Finished downloading %s" % (file_name)


def download_file_with_basic_auth(url, file_name, username, password):
    p = urllib2.HTTPPasswordMgrWithDefaultRealm()

    p.add_password(None, url, username, password)

    handler = urllib2.HTTPBasicAuthHandler(p)
    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)

    data = urlopen_with_retry(url).read()
    f = open(file_name, "wb")
    f.write(data)
    f.close()
    print "Finished downloading %s" % (file_name)


def check_file_for_contents(file_path):
    handle_process_success_or_failure(os.stat(file_path).st_size != 0, file_path)


def check_input_and_output_tsvs_for_same_number_variants(tsvIn, tsvOut, numVariantsRemoved=0):
    tsvInput = csv.DictReader(open(tsvIn, 'r'), delimiter='\t')
    numVariantsIn = len(list(tsvInput))
    tsvOutput = csv.DictReader(open(tsvOut, 'r'), delimiter='\t')
    numVariantsOut = len(list(tsvOutput))
    print("Number of variants in input: %s \nNumber of variants in output: %s \n Number of variants removed: %s\n" % (numVariantsIn, numVariantsOut, numVariantsRemoved))
    handle_process_success_or_failure(numVariantsIn - numVariantsRemoved == numVariantsOut, tsvOut)


def handle_process_success_or_failure(process_succeeded, file_path):
    file_name = file_path.split('/')[-1]
    if process_succeeded is True:
        print("Completed writing %s. \n" % (file_name))
    else:
        now = str(datetime.datetime.utcnow())
        file_directory = os.path.dirname(file_path)
        failed_file_name = "FAILED_" + now + "_" + file_name
        os.rename(file_path, file_directory + "/" + failed_file_name)
        print("**** Failure creating %s ****\n" % (file_name))


def extract_file(archive_path, tmp_dir, file_path):
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extract(file_path, tmp_dir)

        return tmp_dir + '/' + file_path


#######################################
# Default Globals / Env / Directories #
#######################################


DEFAULT_BRCA_RESOURCES_DIR = (os.path.abspath('../brca/brca-resources'))
DEFAULT_OUTPUT_DIR = (os.path.abspath('../brca/pipeline-data/data/pipeline_input'))
DEFAULT_FILE_PARENT_DIR = (os.path.abspath('../brca/pipeline-data/data'))

luigi_dir = os.getcwd()

bic_method_dir = os.path.abspath('../bic')
clinvar_method_dir = os.path.abspath('../clinvar')
esp_method_dir = os.path.abspath('../esp')
lovd_method_dir = os.path.abspath('../lovd')
g1k_method_dir = os.path.abspath('../1000_Genomes')
enigma_method_dir = os.path.abspath('../enigma')
functional_assays_method_dir = os.path.abspath('../functional_assays')
data_merging_method_dir = os.path.abspath('../data_merging')
priors_method_dir = os.path.abspath('../splicing')
priors_filter_method_dir = os.path.abspath('../splicingfilter')
utilities_method_dir = os.path.abspath('../utilities')


class BRCATask(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())
    u = luigi.Parameter(default="UNKNOWN_USER")
    p = luigi.Parameter(default="UNKNOWN_PASSWORD", significant=False)

    resources_dir = luigi.Parameter(default=DEFAULT_BRCA_RESOURCES_DIR,
                                    description='directory to store brca-resources data')


    output_dir = luigi.Parameter(default=DEFAULT_OUTPUT_DIR,
                                 description='directory to store output files')

    output_dir_host = luigi.Parameter(default=DEFAULT_OUTPUT_DIR,
                                 description='directory to store output files wrt to host file system (needed for setting up volume mapping for running docker inside docker)')

    file_parent_dir = luigi.Parameter(default=DEFAULT_FILE_PARENT_DIR,
                                      description='directory to store all individual task related files')

    previous_release_tar = luigi.Parameter(default=None, description='path to previous release tar for diffing versions \
                                       and producing change types for variants')

    priors_references_dir = luigi.Parameter(default=None, description='directory to store priors references data')

    priors_docker_image_name = luigi.Parameter(default=None, description='docker image name for priors calculation')

    release_notes = luigi.Parameter(default=None, description='notes for release, must be a .txt file')

    def run(self):
        pass

###############################################
#                   CLINVAR                   #
###############################################


class DownloadLatestClinvarData(BRCATask):
    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/ClinVar/ClinVarFullRelease_00-latest.xml.gz")

    def run(self):
        clinvar_file_dir = create_path_if_nonexistent(self.file_parent_dir + "/ClinVar")
        os.chdir(clinvar_file_dir)

        clinvar_data_url = "ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ClinVarFullRelease_00-latest.xml.gz"
        download_file_and_display_progress(clinvar_data_url)


@requires(DownloadLatestClinvarData)
class ConvertLatestClinvarDataToXML(BRCATask):

    def output(self):
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts/")
        return luigi.LocalTarget(self.file_parent_dir + "/ClinVar/ClinVarBrca.xml")

    def run(self):
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts/")
        clinvar_file_dir = self.file_parent_dir + "/ClinVar"
        os.chdir(clinvar_method_dir)

        clinvar_xml_file = clinvar_file_dir + "/ClinVarBrca.xml"
        writable_clinvar_xml_file = open(clinvar_xml_file, "w")
        args = ["python", "filter_clinvar_brca.py", self.input().path, self.output().path]
        print "Running clinVarBrca.py with the following args: %s. This takes a while..." % (args)
        sp = subprocess.Popen(args, stdout=writable_clinvar_xml_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(clinvar_xml_file)

@requires(ConvertLatestClinvarDataToXML)
class ConvertClinvarXMLToTXT(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/ClinVar/ClinVarBrca.txt")

    def run(self):
        clinvar_file_dir = self.file_parent_dir + "/ClinVar"
        os.chdir(clinvar_method_dir)

        clinvar_txt_file = clinvar_file_dir + "/ClinVarBrca.txt"
        writable_clinvar_txt_file = open(clinvar_txt_file, "w")
        args = ["python", "clinVarParse.py", clinvar_file_dir + "/ClinVarBrca.xml", "--assembly", "GRCh38"]
        print "Running clinVarParse.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_clinvar_txt_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(clinvar_txt_file)


@requires(ConvertClinvarXMLToTXT)
class ConvertClinvarTXTToVCF(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/ClinVar/ClinVarBrca.vcf")

    def run(self):
        clinvar_file_dir = self.file_parent_dir + "/ClinVar"
        clinvar_vcf_file = clinvar_file_dir + "/ClinVarBrca.vcf"

        os.chdir(data_merging_method_dir)
        args = ["python", "convert_tsv_to_vcf.py", "-i", clinvar_file_dir + "/ClinVarBrca.txt", "-o",
                clinvar_file_dir + "/ClinVarBrca.vcf", "-s", "ClinVar"]
        print "Running convert_tsv_to_vcf.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(clinvar_vcf_file)


@requires(ConvertClinvarTXTToVCF)
class CopyClinvarVCFToOutputDir(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.output_dir + "/ClinVarBrca.vcf")

    def run(self):
        clinvar_file_dir = self.file_parent_dir + "/ClinVar"
        create_path_if_nonexistent(self.output_dir)

        copy(self.file_parent_dir + "/ClinVar/ClinVarBrca.vcf", self.output_dir)
        check_file_for_contents(self.output_dir + "/ClinVarBrca.vcf")


###############################################
#                     ESP                     #
###############################################


class DownloadLatestESPData(BRCATask):
    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/ESP/ESP6500SI-V2-SSA137.GRCh38-liftover.snps_indels.vcf.tar.gz")

    def run(self):
        esp_file_dir = create_path_if_nonexistent(self.file_parent_dir + '/ESP')
        os.chdir(esp_file_dir)

        esp_data_url = "http://evs.gs.washington.edu/evs_bulk_data/ESP6500SI-V2-SSA137.GRCh38-liftover.snps_indels.vcf.tar.gz"
        download_file_and_display_progress(esp_data_url)


@requires(DownloadLatestESPData)
class DecompressESPTarfile(BRCATask):

    def output(self):
        esp_file_dir = self.file_parent_dir + '/ESP'

        return {'chr17': luigi.LocalTarget(esp_file_dir + "/ESP6500SI-V2-SSA137.GRCh38-liftover.chr17.snps_indels.vcf"),
                'chr13': luigi.LocalTarget(esp_file_dir + "/ESP6500SI-V2-SSA137.GRCh38-liftover.chr13.snps_indels.vcf")}

    def run(self):
        esp_file_dir = self.file_parent_dir + '/ESP'
        esp_data_url = "http://evs.gs.washington.edu/evs_bulk_data/ESP6500SI-V2-SSA137.GRCh38-liftover.snps_indels.vcf.tar.gz"
        file_name = esp_data_url.split('/')[-1]
        os.chdir(esp_file_dir)

        tar = tarfile.open(file_name, "r:gz")
        tar.extractall()
        tar.close()
        print "Finished extracting files from %s" % (file_name)


@requires(DecompressESPTarfile)
class ExtractESPDataForBRCA1Region(BRCATask):

    def output(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        return luigi.LocalTarget(esp_file_dir + "/esp.brca1.vcf")

    def run(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        os.chdir(esp_method_dir)

        brca1_region_file = esp_file_dir + "/ESP6500SI-V2-SSA137.GRCh38-liftover.chr17.snps_indels.vcf"
        brca1_region_output = esp_file_dir + "/esp.brca1.vcf"
        args = ["python", "espExtract.py", brca1_region_file, "--start",
                "43044295", "--end", "43125483", "--full", "1", "-o", brca1_region_output]
        print "Calling espExtract.py for BRCA1 region with the following arguments: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(brca1_region_output)


@requires(ExtractESPDataForBRCA1Region)
class ExtractESPDataForBRCA2Region(BRCATask):

    def output(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        return luigi.LocalTarget(esp_file_dir + "/esp.brca2.vcf")

    def run(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        os.chdir(esp_method_dir)
        brca2_region_file = esp_file_dir + '/ESP6500SI-V2-SSA137.GRCh38-liftover.chr13.snps_indels.vcf'
        brca2_region_output = esp_file_dir + "/esp.brca2.vcf"

        args = ["python", "espExtract.py", brca2_region_file, "--start", "32315473",
                "--end", "32400266", "--full", "1", "-o", brca2_region_output]
        print "Calling espExtract.py for BRCA 2 region with the following arguments: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)


@requires(ExtractESPDataForBRCA2Region)
class ConcatenateESPBRCA12Data(BRCATask):

    def output(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        return luigi.LocalTarget(esp_file_dir + "/esp.brca12.hg38.vcf")

    def run(self):
        # Note: requires correct installation of VCF tools and export PERL5LIB=/path/to/your/vcftools-directory/src/perl/ in path
        esp_file_dir = self.file_parent_dir + "/ESP"
        brca1_region_output = esp_file_dir + "/esp.brca1.vcf"
        brca2_region_output = esp_file_dir + "/esp.brca2.vcf"
        concatenated_brca_output_file = esp_file_dir + "/esp.brca12.hg38.vcf"
        writable_concatenated_brca_output_file = open(concatenated_brca_output_file, 'w')
        args = ["vcf-concat", brca1_region_output, brca2_region_output]
        print "Calling vcf-concat with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_concatenated_brca_output_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        writable_concatenated_brca_output_file.close()
        check_file_for_contents(concatenated_brca_output_file)
        print "Concatenation complete."


@requires(ConcatenateESPBRCA12Data)
class SortConcatenatedESPBRCA12Data(BRCATask):

    def output(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        return luigi.LocalTarget(esp_file_dir + "/esp.brca12.sorted.hg38.vcf")

    def run(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        sorted_concatenated_brca_output_file = esp_file_dir + "/esp.brca12.sorted.hg38.vcf"
        concatenated_brca_output_file = esp_file_dir + "/esp.brca12.hg38.vcf"
        writable_sorted_concatenated_brca_output_file = open(sorted_concatenated_brca_output_file, 'w')
        args = ["vcf-sort", concatenated_brca_output_file]
        print "Calling vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_sorted_concatenated_brca_output_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        writable_sorted_concatenated_brca_output_file.close()
        check_file_for_contents(sorted_concatenated_brca_output_file)
        print "Sorting of concatenated files complete."


@requires(SortConcatenatedESPBRCA12Data)
class CopyESPOutputToOutputDir(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.output_dir + "/esp.brca12.sorted.hg38.vcf")

    def run(self):
        esp_file_dir = self.file_parent_dir + "/ESP"
        create_path_if_nonexistent(self.output_dir)

        copy(esp_file_dir + "/esp.brca12.sorted.hg38.vcf", self.output_dir)
        check_file_for_contents(self.output_dir + "/esp.brca12.sorted.hg38.vcf")


###############################################
#                     BIC                     #
###############################################


class DownloadBRCA1BICData(BRCATask):
    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/brca1_data.txt")

    def run(self):
        bic_file_dir = create_path_if_nonexistent(self.file_parent_dir + '/BIC')

        os.chdir(bic_file_dir)

        brca1_data_url = "https://research.nhgri.nih.gov/projects/bic/Member/cgi-bin/bic_query_result.cgi/brca1_data.txt?table=brca1_exons&download=1&submit=Download"
        brca1_file_name = "brca1_data.txt"
        download_file_with_basic_auth(brca1_data_url, brca1_file_name, self.u, self.p)


@requires(DownloadBRCA1BICData)
class DownloadBRCA2BICData(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/brca2_data.txt")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        os.chdir(bic_file_dir)

        brca2_data_url = "https://research.nhgri.nih.gov/projects/bic/Member/cgi-bin/bic_query_result.cgi/brca2_data.txt?table=brca2_exons&download=1&submit=Download"
        brca2_file_name = "brca2_data.txt"
        download_file_with_basic_auth(brca2_data_url, brca2_file_name, self.u, self.p)


@requires(DownloadBRCA2BICData)
class ConvertBRCA1BICDataToVCF(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/bic_brca1.hg19.vcf")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        os.chdir(bic_method_dir)

        # Note: output file doesn't need to be opened because it's opened inside ./bic2vcf
        bic_brca1_vcf_file = bic_file_dir + "/bic_brca1.hg19.vcf"

        args = ["./bic2vcf", "-i", bic_file_dir + "/brca1_data.txt", "-o", bic_brca1_vcf_file, "-b", "1", "-g",
                self.resources_dir + "/hg19.fa", "-r", self.resources_dir + "/refseq_annotation.hg19.gp", "-a",
                bic_method_dir + "/bicAnnotation"]
        print "Converting BRCA1 BIC data to vcf with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(bic_brca1_vcf_file)


@requires(ConvertBRCA1BICDataToVCF)
class ConvertBRCA2BICDataToVCF(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/bic_brca2.hg19.vcf")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        os.chdir(bic_method_dir)

        # Note: output file doesn't need to be opened because it's opened inside ./bic2vcf
        bic_brca2_vcf_file = bic_file_dir + "/bic_brca2.hg19.vcf"

        args = ["./bic2vcf", "-i", bic_file_dir + "/brca2_data.txt", "-o", bic_brca2_vcf_file, "-b", "2", "-g",
                self.resources_dir + "/hg19.fa", "-r", self.resources_dir + "/refseq_annotation.hg19.gp", "-a",
                bic_method_dir + "/bicAnnotation"]
        print "Converting BRCA2 BIC data to vcf with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(bic_brca2_vcf_file)


@requires(ConvertBRCA2BICDataToVCF)
class ConcatenateBRCA12BICData(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/bic_brca12.hg19.vcf")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'

        bic_brca12_vcf_file = bic_file_dir + "/bic_brca12.hg19.vcf"
        writable_bic_brca12_vcf_file = open(bic_brca12_vcf_file, 'w')
        args = ["vcf-concat", bic_file_dir + "/bic_brca1.hg19.vcf", bic_file_dir + "/bic_brca2.hg19.vcf"]
        print "Concatenating BRCA1/2 BIC data with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_bic_brca12_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(bic_brca12_vcf_file)


@requires(ConcatenateBRCA12BICData)
class CrossmapConcatenatedBICData(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/bic_brca12.hg38.vcf")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        brca_resources_dir = self.resources_dir

        bic_brca12_hg38_vcf_file = bic_file_dir + "/bic_brca12.hg38.vcf"
        writable_bic_brca12_hg38_vcf_file = open(bic_brca12_hg38_vcf_file, 'w')
        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                bic_file_dir + "/bic_brca12.hg19.vcf", brca_resources_dir + "/hg38.fa",
                bic_file_dir + "/bic_brca12.hg38.vcf"]
        print "Crossmapping concatenated BIC data with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_bic_brca12_hg38_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(bic_brca12_hg38_vcf_file)


@requires(CrossmapConcatenatedBICData)
class SortBICData(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(bic_file_dir + "/bic_brca12.sorted.hg38.vcf")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'

        sorted_bic_output_file = bic_file_dir + "/bic_brca12.sorted.hg38.vcf"
        writable_sorted_bic_output_file = open(sorted_bic_output_file, 'w')
        args = ["vcf-sort", bic_file_dir + "/bic_brca12.hg38.vcf"]
        print "Sorting BIC data with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_sorted_bic_output_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(sorted_bic_output_file)


@requires(SortBICData)
class CopyBICOutputToOutputDir(BRCATask):

    def output(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        return luigi.LocalTarget(self.output_dir + "/bic_brca12.sorted.hg38.vcf")

    def run(self):
        bic_file_dir = self.file_parent_dir + '/BIC'
        create_path_if_nonexistent(self.output_dir)

        copy(bic_file_dir + "/bic_brca12.sorted.hg38.vcf", self.output_dir)
        check_file_for_contents(self.output_dir + "/bic_brca12.sorted.hg38.vcf")


###############################################
#                  exLOVD                     #
###############################################


class ExtractDataFromLatestEXLOVD(BRCATask):
    def output(self):
        ex_lovd_file_dir = self.file_parent_dir + '/exLOVD'

        return {'brca1': luigi.LocalTarget(ex_lovd_file_dir + "/BRCA1.txt"),
                'brca2': luigi.LocalTarget(ex_lovd_file_dir + "/BRCA2.txt")}

    def run(self):
        ex_lovd_file_dir = create_path_if_nonexistent(self.file_parent_dir + '/exLOVD')

        os.chdir(lovd_method_dir)

        ex_lovd_data_host_url = "http://hci-exlovd.hci.utah.edu/"
        args = ["extract_data.py", "-u", ex_lovd_data_host_url, "-l", "BRCA1", "BRCA2", "-o", ex_lovd_file_dir]
        print "Running extract_data.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Extracted data from %s." % (ex_lovd_data_host_url)


@requires(ExtractDataFromLatestEXLOVD)
class ConvertEXLOVDBRCA1ExtractToVCF(BRCATask):

    def output(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        return luigi.LocalTarget(ex_lovd_file_dir + "/exLOVD_brca1.hg19.vcf")

    def run(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts/")

        os.chdir(lovd_method_dir)

        args = ["./lovd2vcf.py", "-i", ex_lovd_file_dir + "/BRCA1.txt", "-o",
                ex_lovd_file_dir + "/exLOVD_brca1.hg19.vcf", "-a", "exLOVDAnnotation",
                "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g",
                brca_resources_dir + "/hg19.fa", "-e", artifacts_dir + "/exLOVD_BRCA1_error_variants.txt",
                "-s", "exLOVD"]
        print "Running lovd2vcf with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(ex_lovd_file_dir + "/exLOVD_brca1.hg19.vcf")


@requires(ConvertEXLOVDBRCA1ExtractToVCF)
class ConvertEXLOVDBRCA2ExtractToVCF(BRCATask):

    def output(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        return luigi.LocalTarget(ex_lovd_file_dir + "/exLOVD_brca2.hg19.vcf")

    def run(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts/")

        args = ["./lovd2vcf.py", "-i", ex_lovd_file_dir + "/BRCA2.txt", "-o",
                ex_lovd_file_dir + "/exLOVD_brca2.hg19.vcf", "-a", "exLOVDAnnotation",
                "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g",
                brca_resources_dir + "/hg19.fa", "-e", artifacts_dir + "/exLOVD_BRCA2_error_variants.txt",
                "-s", "exLOVD"]
        print "Running lovd2vcf with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(ex_lovd_file_dir + "/exLOVD_brca2.hg19.vcf")


@requires(ConvertEXLOVDBRCA2ExtractToVCF)
class ConcatenateEXLOVDVCFFiles(BRCATask):

    def output(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        return luigi.LocalTarget(ex_lovd_file_dir + "/exLOVD_brca12.hg19.vcf")

    def run(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"

        ex_lovd_brca12_hg19_vcf_file = ex_lovd_file_dir + "/exLOVD_brca12.hg19.vcf"
        writable_ex_lovd_brca12_hg19_vcf_file = open(ex_lovd_brca12_hg19_vcf_file, 'w')
        args = ["vcf-concat", ex_lovd_file_dir + "/exLOVD_brca1.hg19.vcf", ex_lovd_file_dir + "/exLOVD_brca2.hg19.vcf"]
        print "Running vcf-concat with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_ex_lovd_brca12_hg19_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(ex_lovd_file_dir + "/exLOVD_brca12.hg19.vcf")


@requires(ConcatenateEXLOVDVCFFiles)
class CrossmapConcatenatedEXLOVDData(BRCATask):

    def output(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        return luigi.LocalTarget(ex_lovd_file_dir + "/exLOVD_brca12.hg38.vcf")

    def run(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        brca_resources_dir = self.resources_dir

        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                ex_lovd_file_dir + "/exLOVD_brca12.hg19.vcf", brca_resources_dir + "/hg38.fa",
                ex_lovd_file_dir + "/exLOVD_brca12.hg38.vcf"]
        print "Running CrossMap.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(ex_lovd_file_dir + "/exLOVD_brca12.hg38.vcf")


@requires(CrossmapConcatenatedEXLOVDData)
class SortEXLOVDOutput(BRCATask):

    def output(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        return luigi.LocalTarget(ex_lovd_file_dir + "/exLOVD_brca12.sorted.hg38.vcf")

    def run(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"

        sorted_ex_lovd_output_file = ex_lovd_file_dir + "/exLOVD_brca12.sorted.hg38.vcf"
        writable_sorted_ex_lovd_output_file = open(sorted_ex_lovd_output_file, 'w')
        args = ["vcf-sort", ex_lovd_file_dir + "/exLOVD_brca12.hg38.vcf"]
        print "Running vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_sorted_ex_lovd_output_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Sorted BRCA1/2 hg38 vcf file into %s" % (writable_sorted_ex_lovd_output_file)

        check_file_for_contents(ex_lovd_file_dir + "/exLOVD_brca12.sorted.hg38.vcf")


@requires(SortEXLOVDOutput)
class CopyEXLOVDOutputToOutputDir(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.output_dir + "/exLOVD_brca12.sorted.hg38.vcf")

    def run(self):
        ex_lovd_file_dir = self.file_parent_dir + "/exLOVD"
        create_path_if_nonexistent(self.output_dir)

        copy(ex_lovd_file_dir + "/exLOVD_brca12.sorted.hg38.vcf", self.output_dir)

        check_file_for_contents(self.output_dir + "/exLOVD_brca12.sorted.hg38.vcf")


###############################################
#                sharedLOVD                   #
###############################################


class DownloadLOVDInputFile(BRCATask):
    """ Downloads the shared LOVD data

    If the pipeline is run on a machine from which it is not possible to download the data (currently IP based authentication)
    the file can be manually staged in the path of `lovd_data_file`. In this case, the task will not be run.
    """

    lovd_data_file = luigi.Parameter(default='', description='path, where the shared LOVD data will be stored')

    shared_lovd_data_url = luigi.Parameter(default='https://databases.lovd.nl/shared/export/BRCA',
                                            description='URL to download shared LOVD data from')

    def output(self):
        if len(str(self.lovd_data_file)) == 0:
            path = self.file_parent_dir + "/LOVD/BRCA.txt"
        else:
            path = str(self.lovd_data_file)

        return luigi.LocalTarget(path)

    def run(self):
        create_path_if_nonexistent(os.path.dirname(self.output().path))
        data = urlopen_with_retry(self.shared_lovd_data_url).read()
        with open(self.output().path, "wb") as f:
            f.write(data)


@requires(DownloadLOVDInputFile)
class NormalizeLOVDSubmissions(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/LOVD/LOVD_normalized.tsv")

    def run(self):
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts")

        os.chdir(lovd_method_dir)

        args = ["python", "normalizeLOVDSubmissions.py", "-i", self.input().path, "-o",
                self.output().path]

        print "Running separateFunctionalAnalysisTechniqueAndResult with the following args: %s" % (args)

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(self.output().path)


@requires(NormalizeLOVDSubmissions)
class CombineEquivalentLOVDSubmissions(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/LOVD/LOVD_normalized_combined.tsv")

    def run(self):
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts")

        os.chdir(lovd_method_dir)

        args = ["python", "combineEquivalentVariantSubmissions.py", "-i", self.input().path, "-o",
                self.output().path]

        print "Running combineEquivalentVariantSubmissions.py with the following args: %s" % (args)

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(self.output().path)


@requires(CombineEquivalentLOVDSubmissions)
class ConvertSharedLOVDToVCF(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/LOVD/sharedLOVD_brca12.hg19.vcf")

    def run(self):
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts")

        os.chdir(lovd_method_dir)

        args = ["python", "lovd2vcf.py", "-i", self.input().path, "-o",
                self.output().path, "-a", "sharedLOVDAnnotation",
                "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g",
                brca_resources_dir + "/hg19.fa", "-e", artifacts_dir + "/LOVD_error_variants.txt",
                "-s", "LOVD"]

        print "Running lovd2vcf with the following args: %s" % (args)

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(self.output().path)


@requires(ConvertSharedLOVDToVCF)
class CrossmapConcatenatedSharedLOVDData(BRCATask):

    def output(self):
        lovd_file_dir = self.file_parent_dir + "/LOVD"
        return luigi.LocalTarget(lovd_file_dir + "/sharedLOVD_brca12.hg38.vcf")

    def run(self):
        lovd_file_dir = self.file_parent_dir + "/LOVD"
        brca_resources_dir = self.resources_dir

        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                lovd_file_dir + "/sharedLOVD_brca12.hg19.vcf", brca_resources_dir + "/hg38.fa",
                lovd_file_dir + "/sharedLOVD_brca12.hg38.vcf"]
        print "Running CrossMap.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(lovd_file_dir + "/sharedLOVD_brca12.hg38.vcf")


@requires(CrossmapConcatenatedSharedLOVDData)
class SortSharedLOVDOutput(BRCATask):

    def output(self):
        lovd_file_dir = self.file_parent_dir + "/LOVD"
        return luigi.LocalTarget(lovd_file_dir + "/sharedLOVD_brca12.sorted.hg38.vcf")

    def run(self):
        lovd_file_dir = self.file_parent_dir + "/LOVD"

        sorted_lovd_output_file = lovd_file_dir + "/sharedLOVD_brca12.sorted.hg38.vcf"
        writable_sorted_lovd_output_file = open(sorted_lovd_output_file, 'w')
        args = ["vcf-sort", lovd_file_dir + "/sharedLOVD_brca12.hg38.vcf"]
        print "Running vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_sorted_lovd_output_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Sorted BRCA1/2 hg38 vcf file into %s" % (writable_sorted_lovd_output_file)

        check_file_for_contents(lovd_file_dir + "/sharedLOVD_brca12.sorted.hg38.vcf")


@requires(SortSharedLOVDOutput)
class CopySharedLOVDOutputToOutputDir(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.output_dir + "/sharedLOVD_brca12.sorted.hg38.vcf")

    def run(self):
        lovd_file_dir = self.file_parent_dir + "/LOVD"
        create_path_if_nonexistent(self.output_dir)

        copy(lovd_file_dir + "/sharedLOVD_brca12.sorted.hg38.vcf", self.output_dir)

        check_file_for_contents(self.output_dir + "/sharedLOVD_brca12.sorted.hg38.vcf")


###############################################
#                    G1K                      #
###############################################


class DownloadG1KCHR13GZ(BRCATask):
    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz")

    def run(self):
        g1k_file_dir = create_path_if_nonexistent(self.file_parent_dir + '/G1K')

        os.chdir(g1k_file_dir)

        chr13_vcf_gz_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz"
        download_file_and_display_progress(chr13_vcf_gz_url)


@requires(DownloadG1KCHR13GZ)
class DownloadG1KCHR17GZ(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        os.chdir(g1k_file_dir)

        chr17_vcf_gz_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz"
        download_file_and_display_progress(chr17_vcf_gz_url)


@requires(DownloadG1KCHR17GZ)
class DownloadG1KCHR13GZTBI(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        os.chdir(g1k_file_dir)

        chr13_vcf_gz_tbi_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi"
        download_file_and_display_progress(chr13_vcf_gz_tbi_url)


@requires(DownloadG1KCHR13GZTBI)
class DownloadG1KCHR17GZTBI(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        os.chdir(g1k_file_dir)

        chr17_vcf_gz_tbi_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi"
        download_file_and_display_progress(chr17_vcf_gz_tbi_url)


@requires(DownloadG1KCHR17GZTBI)
class ExtractCHR13BRCAData(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/chr13_brca2_1000g_GRCh37.vcf")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'

        chr13_brca2_vcf_file = g1k_file_dir + "/chr13_brca2_1000g_GRCh37.vcf"
        writable_chr13_brca2_vcf_file = open(chr13_brca2_vcf_file, "w")
        args = ["tabix", "-h",
                g1k_file_dir + "/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz",
                "13:32889617-32973809"]
        print "Running tabix with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_chr13_brca2_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(chr13_brca2_vcf_file)


@requires(ExtractCHR13BRCAData)
class ExtractCHR17BRCAData(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/chr17_brca1_1000g_GRCh37.vcf")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'

        chr17_brca1_vcf_file = g1k_file_dir + "/chr17_brca1_1000g_GRCh37.vcf"
        writable_chr17_brca1_vcf_file = open(chr17_brca1_vcf_file, "w")
        args = ["tabix", "-h",
                g1k_file_dir + "/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz",
                "17:41196312-41277500"]
        print "Running tabix with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_chr17_brca1_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(chr17_brca1_vcf_file)


@requires(ExtractCHR17BRCAData)
class ConcatenateG1KData(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/brca12_1000g_GRCh37.vcf")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        concatenated_g1k_vcf = g1k_file_dir + "/brca12_1000g_GRCh37.vcf"
        writable_concatenated_g1k_vcf = open(concatenated_g1k_vcf, "w")
        args = ["vcf-concat", g1k_file_dir + "/chr13_brca2_1000g_GRCh37.vcf",
                g1k_file_dir + "/chr17_brca1_1000g_GRCh37.vcf"]
        print "Running vcf-concat with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_concatenated_g1k_vcf, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(concatenated_g1k_vcf)


@requires(ConcatenateG1KData)
class CrossmapConcatenatedG1KData(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/1000G_brca.hg38.vcf")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        brca_resources_dir = self.resources_dir

        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                g1k_file_dir + "/brca12_1000g_GRCh37.vcf", brca_resources_dir + "/hg38.fa",
                g1k_file_dir + "/1000G_brca.hg38.vcf"]
        print "Running CrossMap.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(g1k_file_dir + "/1000G_brca.hg38.vcf")


@requires(CrossmapConcatenatedG1KData)
class SortG1KData(BRCATask):

    def output(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        return luigi.LocalTarget(g1k_file_dir + "/1000G_brca.sorted.hg38.vcf")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'

        sorted_g1k_output_file = g1k_file_dir + "/1000G_brca.sorted.hg38.vcf"
        writable_sorted_g1k_output_file = open(sorted_g1k_output_file, 'w')
        args = ["vcf-sort", g1k_file_dir + "/1000G_brca.hg38.vcf"]
        print "Running vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_sorted_g1k_output_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(g1k_file_dir + "/1000G_brca.sorted.hg38.vcf")


@requires(SortG1KData)
class CopyG1KOutputToOutputDir(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.output_dir + "/1000G_brca.sorted.hg38.vcf")

    def run(self):
        g1k_file_dir = self.file_parent_dir + '/G1K'
        create_path_if_nonexistent(self.output_dir)

        copy(g1k_file_dir + "/1000G_brca.sorted.hg38.vcf", self.output_dir)

        check_file_for_contents(self.output_dir + "/1000G_brca.sorted.hg38.vcf")


###############################################
#                    EXAC                     #
###############################################


class DownloadEXACVCFGZFile(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz")

    def run(self):
        exac_file_dir = create_path_if_nonexistent(self.file_parent_dir + '/exac')

        os.chdir(exac_file_dir)

        exac_vcf_gz_url = "ftp://ftp.broadinstitute.org/pub/ExAC_release/current/subsets/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz"
        exac_vcf_gz_file_name = exac_vcf_gz_url.split('/')[-1]
        download_file_and_display_progress(exac_vcf_gz_url, exac_vcf_gz_file_name)


@requires(DownloadEXACVCFGZFile)
class DownloadEXACVCFGZTBIFile(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz.tbi")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        os.chdir(exac_file_dir)

        exac_vcf_gz_tbi_url = "ftp://ftp.broadinstitute.org/pub/ExAC_release/current/subsets/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz.tbi"
        exac_vcf_gz_tbi_file_name = exac_vcf_gz_tbi_url.split('/')[-1]
        download_file_and_display_progress(exac_vcf_gz_tbi_url, exac_vcf_gz_tbi_file_name)


@requires(DownloadEXACVCFGZTBIFile)
class ExtractBRCA1DataFromExac(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/exac.brca1.hg19.vcf")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'

        exac_brca1_hg19_vcf_file = exac_file_dir + "/exac.brca1.hg19.vcf"
        writable_exac_brca1_hg19_vcf_file = open(exac_brca1_hg19_vcf_file, 'w')

        args = ["tabix", "-h", exac_file_dir + "/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz", "17:41196312-41277500"]
        print "Running tabix with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_exac_brca1_hg19_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(exac_brca1_hg19_vcf_file)


@requires(ExtractBRCA1DataFromExac)
class ExtractBRCA2DataFromExac(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/exac.brca2.hg19.vcf")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'

        exac_brca2_hg19_vcf_file = exac_file_dir + "/exac.brca2.hg19.vcf"
        writable_exac_brca2_hg19_vcf_file = open(exac_brca2_hg19_vcf_file, 'w')

        args = ["tabix", "-h", exac_file_dir + "/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz", "13:32889617-32973809"]
        print "Running tabix with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_exac_brca2_hg19_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(exac_brca2_hg19_vcf_file)


@requires(ExtractBRCA2DataFromExac)
class ConcatenateEXACData(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/exac.brca12.hg19.vcf")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'

        exac_brca12_hg19_vcf_file = exac_file_dir + "/exac.brca12.hg19.vcf"
        writable_exac_brca12_hg19_vcf_file = open(exac_brca12_hg19_vcf_file, 'w')
        args = ["vcf-concat", exac_file_dir + "/exac.brca1.hg19.vcf", exac_file_dir + "/exac.brca2.hg19.vcf"]
        print "Running tabix with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_exac_brca12_hg19_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(exac_brca12_hg19_vcf_file)


@requires(ConcatenateEXACData)
class CrossmapEXACData(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/exac.brca12.hg38.vcf")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        brca_resources_dir = self.resources_dir

        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                exac_file_dir + "/exac.brca12.hg19.vcf", brca_resources_dir + "/hg38.fa",
                exac_file_dir + "/exac.brca12.hg38.vcf"]
        print "Running CrossMap.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(exac_file_dir + "/exac.brca12.hg38.vcf")


@requires(CrossmapEXACData)
class SortEXACData(BRCATask):
    def output(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        return luigi.LocalTarget(exac_file_dir + "/exac.brca12.sorted.hg38.vcf")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'

        with self.output().open("w") as vcf_file:
            args = ["vcf-sort", exac_file_dir + "/exac.brca12.hg38.vcf"]
            print "Running tabix with the following args: %s" % (args)
            sp = subprocess.Popen(args, stdout=vcf_file, stderr=subprocess.PIPE)
            print_subprocess_output_and_error(sp)

        check_file_for_contents(exac_file_dir + "/exac.brca12.sorted.hg38.vcf")


@requires(SortEXACData)
class CopyEXACOutputToOutputDir(BRCATask):
    def output(self):
        return luigi.LocalTarget(self.output_dir + "/exac.brca12.sorted.hg38.vcf")

    def run(self):
        exac_file_dir = self.file_parent_dir + '/exac'
        create_path_if_nonexistent(self.output_dir)

        copy(exac_file_dir + "/exac.brca12.sorted.hg38.vcf", self.output_dir)

        check_file_for_contents(self.output_dir + "/exac.brca12.sorted.hg38.vcf")


###############################################
#                  ENIGMA                     #
###############################################

@requires(ConvertLatestClinvarDataToXML)
class FilterEnigmaAssertions(BRCATask):
    def output(self):
        out_path = os.path.join(self.file_parent_dir, 'enigma', 'enigma_clinvar.xml')
        return luigi.LocalTarget(out_path)

    def run(self):
        create_path_if_nonexistent(os.path.join(self.file_parent_dir, 'enigma'))
        os.chdir(clinvar_method_dir)

        args = ["python", "filter_enigma_data.py", self.input().path, self.output().path]

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)


@requires(FilterEnigmaAssertions)
class ExtractEnigmaFromClinvar(BRCATask):
    def output(self):
        out_path = os.path.join(self.file_parent_dir, 'enigma', 'enigma_from_clinvar.tsv')
        return luigi.LocalTarget(out_path)

    def run(self):
        os.chdir(clinvar_method_dir)

        args = ["python", "enigma_from_clinvar.py", self.input().path, self.output().path]

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        copy(self.output().path, self.output_dir)


###############################################
#             FUNCTIONAL ASSAYS               #
###############################################



class DownloadFunctionalAssayInputFile(BRCATask):
    # Downloads functional assays

    functional_assays_file = luigi.Parameter(default='', description='path, where the functional assays data will be stored')

    functional_assays_data_url = luigi.Parameter(default='https://brcaexchange.org/backend/downloads/functional_assays.tsv',
                                            description='URL to download functional assays data from')

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/functional_assays/functional_assays.tsv")

    def run(self):
        create_path_if_nonexistent(os.path.dirname(self.output().path))
        data = urlopen_with_retry(self.functional_assays_data_url).read()
        with open(self.output().path, "wb") as f:
            f.write(data)


@requires(DownloadFunctionalAssayInputFile)
class ParseFunctionalAssays(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/functional_assays/functional_assays_clean.tsv")

    def run(self):
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts")

        os.chdir(functional_assays_method_dir)

        args = ["python", "parse_functional_assay_data.py", "-i", self.input().path, "-o",
                self.output().path]

        print "Running parse_functional_assay_data.py with the following args: %s" % (args)

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(self.output().path)


@requires(ParseFunctionalAssays)
class ConvertFunctionalAssaysToVCF(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.file_parent_dir + "/functional_assays/functional_assays.hg19.vcf")

    def run(self):
        brca_resources_dir = self.resources_dir
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts")

        os.chdir(functional_assays_method_dir)

        args = ["python", "functional_assays_to_vcf.py", "-i", self.input().path, "-o",
                self.output().path, "-a", "functionalAssayAnnotation",
                "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g",
                brca_resources_dir + "/hg19.fa", "-e", artifacts_dir + "/functional_assays_error_variants.txt"]

        print "Running functional_assays_to_vcf with the following args: %s" % (args)

        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(self.output().path)


@requires(ConvertFunctionalAssaysToVCF)
class CrossmapFunctionalAssays(BRCATask):

    def output(self):
        functional_assays_file_dir = self.file_parent_dir + "/functional_assays"
        return luigi.LocalTarget(functional_assays_file_dir + "/functional_assays.hg38.vcf")

    def run(self):
        functional_assays_file_dir = self.file_parent_dir + "/functional_assays"
        brca_resources_dir = self.resources_dir

        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                functional_assays_file_dir + "/functional_assays.hg19.vcf", brca_resources_dir + "/hg38.fa",
                functional_assays_file_dir + "/functional_assays.hg38.vcf"]
        print "Running CrossMap.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(functional_assays_file_dir + "/functional_assays.hg38.vcf")


@requires(CrossmapFunctionalAssays)
class SortFunctionalAssays(BRCATask):

    def output(self):
        functional_assays_file_dir = self.file_parent_dir + "/functional_assays"
        return luigi.LocalTarget(functional_assays_file_dir + "/functional_assays.sorted.hg38.vcf")

    def run(self):
        functional_assays_file_dir = self.file_parent_dir + "/functional_assays"

        sorted_functional_assays = functional_assays_file_dir + "/functional_assays.sorted.hg38.vcf"
        writable_sorted_functional_assays = open(sorted_functional_assays, 'w')
        args = ["vcf-sort", functional_assays_file_dir + "/functional_assays.hg38.vcf"]
        print "Running vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=writable_sorted_functional_assays, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Sorted hg38 vcf file into %s" % (writable_sorted_functional_assays)

        check_file_for_contents(functional_assays_file_dir + "/functional_assays.sorted.hg38.vcf")


@requires(SortFunctionalAssays)
class CopyFunctionalAssaysOutputToOutputDir(BRCATask):

    def output(self):
        return luigi.LocalTarget(self.output_dir + "/functional_assays.sorted.hg38.vcf")

    def run(self):
        functional_assays_file_dir = self.file_parent_dir + "/functional_assays"
        create_path_if_nonexistent(self.output_dir)

        copy(functional_assays_file_dir + "/functional_assays.sorted.hg38.vcf", self.output_dir)

        check_file_for_contents(self.output_dir + "/functional_assays.sorted.hg38.vcf")



###############################################
#            VARIANT COMPILATION              #
###############################################


class MergeVCFsIntoTSVFile(BRCATask):
    def output(self):
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts/")
        return luigi.LocalTarget(artifacts_dir + "merged.tsv")

    def run(self):
        artifacts_dir = create_path_if_nonexistent(self.output_dir + "/release/artifacts/")
        brca_resources_dir = self.resources_dir

        os.chdir(data_merging_method_dir)

        args = ["python", "variant_merging.py", "-i", self.output_dir + "/", "-o",
                artifacts_dir, "-p", "-r", brca_resources_dir + "/", "-a", artifacts_dir, "-v"]
        print "Running variant_merging.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(artifacts_dir + "merged.tsv")

@requires(MergeVCFsIntoTSVFile)
class AnnotateMergedOutput(BRCATask):

    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "annotated.tsv")

    def run(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        os.chdir(data_merging_method_dir)

        args = ["python", "add_annotation.py", "-i", artifacts_dir + "merged.tsv",
                "-o", artifacts_dir + "annotated.tsv", "-l", artifacts_dir + "add-annotation.log", "-v"]
        print "Running add_annotation.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        # get number of variants thrown out
        numVariantsRemoved = 0
        with open(artifacts_dir + "add-annotation.log") as fp:
            lines = fp.readlines()
            for line in lines:
                if "ERROR COUNT" in line:
                    # pull integer from error count line
                    numVariantsRemoved = int(filter(str.isdigit, line))

        check_input_and_output_tsvs_for_same_number_variants(artifacts_dir + "merged.tsv",
                                                             artifacts_dir + "annotated.tsv", numVariantsRemoved)


@requires(AnnotateMergedOutput)
class AggregateMergedOutput(BRCATask):

    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "aggregated.tsv")

    def run(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        os.chdir(data_merging_method_dir)

        args = ["python", "aggregate_across_columns.py", "-i", artifacts_dir + "annotated.tsv",
                "-o", artifacts_dir + "aggregated.tsv"]
        print "Running aggregate_across_columns.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_input_and_output_tsvs_for_same_number_variants(artifacts_dir + "annotated.tsv",
                                                             artifacts_dir + "aggregated.tsv")


@requires(AggregateMergedOutput)
class BuildAggregatedOutput(BRCATask):

    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "built.tsv")

    def run(self):
        release_dir = self.output_dir + "/release/"
        artifacts_dir = release_dir + "artifacts/"
        brca_resources_dir = self.resources_dir
        os.chdir(data_merging_method_dir)

        args = ["python", "brca_pseudonym_generator.py", "-i", artifacts_dir + "/aggregated.tsv", "-p",
                "-j", brca_resources_dir + "/hg18.fa",
                "-k", brca_resources_dir + "/hg19.fa",
                "-l", brca_resources_dir + "/hg38.fa",
                "-r", brca_resources_dir + "/refseq_annotation.hg18.gp",
                "-s", brca_resources_dir + "/refseq_annotation.hg19.gp",
                "-t", brca_resources_dir + "/refseq_annotation.hg38.gp",
                "-o", artifacts_dir + "built.tsv",
                "--artifacts_dir", artifacts_dir]
        print "Running brca_pseudonym_generator.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_input_and_output_tsvs_for_same_number_variants(artifacts_dir + "aggregated.tsv",
                                                             artifacts_dir + "built.tsv")


@requires(BuildAggregatedOutput)
class AppendMupitStructure(BRCATask):

    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "built_with_mupit.tsv")

    def run(self):
        release_dir = self.output_dir + "/release/"
        artifacts_dir = release_dir + "artifacts/"
        brca_resources_dir = self.resources_dir
        os.chdir(data_merging_method_dir)

        args = ["python", "getMupitStructure.py", "-i", artifacts_dir + "built.tsv", "-o",
                artifacts_dir + "/built_with_mupit.tsv"]
        print "Running getMupitStructure.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_input_and_output_tsvs_for_same_number_variants(artifacts_dir + "built.tsv",
                                                             artifacts_dir + "built_with_mupit.tsv")


@requires(AppendMupitStructure)
class CalculatePriors(BRCATask):
    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "built_with_priors.tsv")

    def run(self):
        artifacts_dir_host = self.output_dir_host + "/release/artifacts/"
        os.chdir(priors_method_dir)

        args = ['bash', 'calcpriors.sh', self.priors_references_dir,
                artifacts_dir_host, 'built_with_mupit.tsv', 'built_with_priors.tsv', self.priors_docker_image_name]

        print "Running calcpriors.sh with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_input_and_output_tsvs_for_same_number_variants(self.input().path,
                                                             self.output().path)


@requires(CalculatePriors)
class FilterBlacklistedPriors(BRCATask):
    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "built_with_priors_clean.tsv")

    def run(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        os.chdir(priors_filter_method_dir)

        args = ["python", "filterBlacklistedVars.py",
                "--output", artifacts_dir + "built_with_priors_clean.tsv",
                "--blacklisted_vars", "blacklisted_vars.txt",
                "filter",
                artifacts_dir + "built_with_priors.tsv"]

        print "Running filterBlacklistedVars.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        # we only clear a few columns; we shouldn't be gaining or losing any variants
        check_input_and_output_tsvs_for_same_number_variants(self.input().path,
                                                             self.output().path)


@requires(FilterBlacklistedPriors)
class FindMissingReports(BRCATask):
    def output(self):
        artifacts_dir = self.output_dir + "/release/artifacts/"
        return luigi.LocalTarget(artifacts_dir + "missing_reports.log")

    def run(self):
        release_dir = self.output_dir + "/release/"
        artifacts_dir = self.output_dir + "/release/artifacts/"
        os.chdir(data_merging_method_dir)

        args = ["python", "check_for_missing_reports.py", "-b", artifacts_dir + "built_with_priors_clean.tsv", "-r", artifacts_dir,
                "-a", artifacts_dir, "-v"]
        print "Running check_for_missing_reports.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(artifacts_dir + "missing_reports.log")


@requires(FindMissingReports)
class RunDiffAndAppendChangeTypesToOutput(BRCATask):
    def _extract_release_date(self, version_json):
        with open(version_json, 'r') as f:
            j = json.load(f)
            return datetime.datetime.strptime(j['date'], '%Y-%m-%d')


    def output(self):
        release_dir = self.output_dir + "/release/"
        diff_dir = create_path_if_nonexistent(release_dir + "diff/")
        return {'built_with_change_types': luigi.LocalTarget(release_dir + "built_with_change_types.tsv"),
                'removed': luigi.LocalTarget(diff_dir + "removed.tsv"),
                'added': luigi.LocalTarget(diff_dir + "added.tsv"),
                'added_data': luigi.LocalTarget(diff_dir + "added_data.tsv"),
                'diff': luigi.LocalTarget(diff_dir + "diff.txt"),
                'diff_json': luigi.LocalTarget(diff_dir + "diff.json"),
                'README': luigi.LocalTarget(diff_dir + "README.txt")}

    def run(self):
        release_dir = self.output_dir + "/release/"
        artifacts_dir = release_dir + "artifacts/"
        diff_dir = create_path_if_nonexistent(release_dir + "diff/")
        os.chdir(utilities_method_dir)

        tmp_dir = tempfile.mkdtemp()
        previous_data_path = extract_file(self.previous_release_tar, tmp_dir, 'output/release/built_with_change_types.tsv')
        version_json_path = extract_file(self.previous_release_tar, tmp_dir, 'output/release/metadata/version.json')
        previous_release_date = self._extract_release_date(version_json_path)
        previous_release_date_str = datetime.datetime.strftime(previous_release_date, '%m-%d-%Y')

        args = ["python", "releaseDiff.py", "--v2", artifacts_dir + "built_with_priors_clean.tsv", "--v1", previous_data_path,
                "--removed", diff_dir + "removed.tsv", "--added", diff_dir + "added.tsv", "--added_data",
                diff_dir + "added_data.tsv", "--diff", diff_dir + "diff.txt", "--diff_json", diff_dir + "diff.json",
                "--output", release_dir + "built_with_change_types.tsv", "--artifacts_dir", artifacts_dir,
                "--diff_dir", diff_dir, "--v1_release_date", previous_release_date_str, "--reports", "False"]

        print "Running releaseDiff.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        shutil.rmtree(tmp_dir) # cleaning up

        check_input_and_output_tsvs_for_same_number_variants(artifacts_dir + "built_with_priors_clean.tsv",
                                                             release_dir + "built_with_change_types.tsv")


@requires(RunDiffAndAppendChangeTypesToOutput)
class RunDiffAndAppendChangeTypesToOutputReports(BRCATask):
    def _extract_release_date(self, version_json):
        with open(version_json, 'r') as f:
            j = json.load(f)
            return datetime.datetime.strptime(j['date'], '%Y-%m-%d')


    def output(self):
        release_dir = self.output_dir + "/release/"
        diff_dir = create_path_if_nonexistent(release_dir + "diff/")
        return {'reports_with_change_types': luigi.LocalTarget(release_dir + "reports_with_change_types.tsv"),
                'removed_reports': luigi.LocalTarget(diff_dir + "removed_reports.tsv"),
                'added_reports': luigi.LocalTarget(diff_dir + "added_reports.tsv"),
                'added_data_reports': luigi.LocalTarget(diff_dir + "added_data_reports.tsv"),
                'diff_reports': luigi.LocalTarget(diff_dir + "diff_reports.txt"),
                'diff_json_reports': luigi.LocalTarget(diff_dir + "diff_reports.json"),
                'README': luigi.LocalTarget(diff_dir + "README.txt")}

    def run(self):
        release_dir = self.output_dir + "/release/"
        artifacts_dir = release_dir + "artifacts/"
        diff_dir = create_path_if_nonexistent(release_dir + "diff/")
        os.chdir(utilities_method_dir)

        tmp_dir = tempfile.mkdtemp()
        previous_data_path = extract_file(self.previous_release_tar, tmp_dir, 'output/release/artifacts/reports.tsv')
        version_json_path = extract_file(self.previous_release_tar, tmp_dir, 'output/release/metadata/version.json')
        previous_release_date = self._extract_release_date(version_json_path)
        previous_release_date_str = datetime.datetime.strftime(previous_release_date, '%m-%d-%Y')

        args = ["python", "releaseDiff.py", "--v2", artifacts_dir + "reports.tsv", "--v1", previous_data_path,
                "--removed", diff_dir + "removed_reports.tsv", "--added", diff_dir + "added_reports.tsv", "--added_data",
                diff_dir + "added_data_reports.tsv", "--diff", diff_dir + "diff_reports.txt", "--diff_json", diff_dir + "diff_reports.json",
                "--output", release_dir + "reports_with_change_types.tsv", "--artifacts_dir", artifacts_dir,
                "--diff_dir", diff_dir, "--v1_release_date", previous_release_date_str, "--reports", "True"]

        print "Running releaseDiff.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        shutil.rmtree(tmp_dir) # cleaning up

        check_input_and_output_tsvs_for_same_number_variants(artifacts_dir + "reports.tsv",
                                                             release_dir + "reports_with_change_types.tsv")


@requires(RunDiffAndAppendChangeTypesToOutputReports)
class GenerateReleaseNotes(BRCATask):

    def output(self):
        metadata_dir = create_path_if_nonexistent(self.output_dir + "/release/metadata/")
        return luigi.LocalTarget(metadata_dir + "version.json")

    def run(self):
        metadata_dir = self.output_dir + "/release/metadata/"
        os.chdir(data_merging_method_dir)

        args = ["python", "buildVersionMetadata.py", "--date", str(self.date), "--notes", self.release_notes,
                "--output", metadata_dir + "version.json"]
        print "Running buildVersionMetadata.py with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(metadata_dir + "version.json")

@requires(GenerateReleaseNotes)
class TopLevelReadme(BRCATask):
    def output(self):
        top_level_readme_dest = os.path.join(self.output_dir, "README.txt")
        return luigi.LocalTarget(top_level_readme_dest)

    def run(self):
        top_level_readme_src = os.path.abspath(
            os.path.join(os.path.realpath(__file__), os.pardir, os.pardir, "top_level_readme.txt"))

        shutil.copyfile(top_level_readme_src, self.output().path)

@requires(TopLevelReadme)
class GenerateMD5Sums(BRCATask):
    def output(self):
        return luigi.LocalTarget(self.output_dir + "/md5sums.txt")

    def run(self):
        output_dir = self.output_dir
        md5sumsFile = output_dir + "/md5sums.txt"

        os.chdir(utilities_method_dir)

        args = ["python", "generateMD5Sums.py", "-i", output_dir, "-o", md5sumsFile]
        print "Generating md5sums with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        check_file_for_contents(md5sumsFile)


@requires(GenerateMD5Sums)
class GenerateReleaseArchive(BRCATask):

    def getArchiveName(self):
        # Format archive filename as release-mm-dd-yy.tar.gz
        return "release-" + self.date.strftime("%x").replace('/', '-') + ".tar.gz"

    def getArchiveParentDirectory(self):
        return os.path.dirname(self.output_dir) + "/"

    def output(self):
        return luigi.LocalTarget(self.getArchiveParentDirectory() + self.getArchiveName())

    def run(self):
        os.chdir(self.getArchiveParentDirectory())
        with tarfile.open(self.getArchiveParentDirectory() + self.getArchiveName(), "w:gz") as tar:
            tar.add(self.output_dir, arcname=os.path.basename(self.output_dir))


###############################################
#              MASTER RUN TASK                #
###############################################


class RunAll(BRCATask, luigi.WrapperTask):
    def requires(self):
        param_map = {
            'date': self.date,
            'u': self.u,
            'p': self.p,
            'resources_dir': self.resources_dir,
            'output_dir': self.output_dir,
            'output_dir_host': self.output_dir_host,
            'file_parent_dir': self.file_parent_dir,
            'previous_release_tar': self.previous_release_tar,
            'priors_references_dir': self.priors_references_dir,
            'priors_docker_image_name': self.priors_docker_image_name,
            'release_notes': self.release_notes
        }

        yield GenerateReleaseArchive(**param_map)

        yield CopyClinvarVCFToOutputDir(**param_map)
        yield CopyESPOutputToOutputDir(**param_map)
        yield CopyBICOutputToOutputDir(**param_map)
        yield CopyG1KOutputToOutputDir(**param_map)
        yield CopyEXACOutputToOutputDir(**param_map)
        yield CopyEXLOVDOutputToOutputDir(**param_map)
        yield CopySharedLOVDOutputToOutputDir(**param_map)
        yield CopyFunctionalAssaysOutputToOutputDir(**param_map)
        yield ExtractEnigmaFromClinvar(**param_map)
