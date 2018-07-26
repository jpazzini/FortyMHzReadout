#define _BSD_SOURCE
#define _XOPEN_SOURCE 500
#include <assert.h>
#include <fcntl.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdint.h>
#include <inttypes.h>
#include <limits.h>

#include <pthread.h> 

static int verbosity = 0;
static int read_back = 0;
static int no_write = 0;
static int allowed_accesses = 1;

static struct option const long_opts[] =
{
  {"device", required_argument, NULL, 'd'},
  {"address", required_argument, NULL, 'a'},
  {"size", required_argument, NULL, 's'},
  {"offset", required_argument, NULL, 'o'},
  {"count", required_argument, NULL, 'c'},
  {"verbose", no_argument, NULL, 'v'},
  {"unpacked", required_argument, NULL, 'f'},
  {"file", required_argument, NULL, 'f'},
  {"help", no_argument, NULL, 'h'},
  {0, 0, 0, 0}
};

typedef struct _tr_arg_t {
    void * buffer;
    size_t size;
    int fpga_fd;
    uint32_t addr;
    int rc;
    uint64_t dummy;
    FILE * fileraw_fd;
    FILE * fileunpack_fd;
} tr_arg_t;


static int run_dma(char *devicename, uint32_t addr, uint32_t size, uint32_t offset, uint32_t count, char *filenameraw, char *filenameunpack);


#define DEVICE_NAME_DEFAULT "/dev/xdma0_c2h_0"
#define SIZE_DEFAULT (1024)
#define COUNT_DEFAULT (10)
#define RAW_OUTPUT_NAME_DEFAULT "output_raw.dat"
#define UNPACKED_OUTPUT_NAME_DEFAULT "output_unpacked.txt"

static void usage(const char* name)
{
  int i = 0;
  printf("%s\n\n", name);
  printf("usage: %s [OPTIONS]\n\n", name);

  printf("  -%c (--%s) device (defaults to %s)\n", 				long_opts[i].val, long_opts[i].name, DEVICE_NAME_DEFAULT	 ); i++;
  printf("  -%c (--%s) address of the start address on the AXI bus\n", 		long_opts[i].val, long_opts[i].name				 ); i++;
  printf("  -%c (--%s) size of a single transfer in bytes, default is %d.\n", 	long_opts[i].val, long_opts[i].name, SIZE_DEFAULT		 ); i++;
  printf("  -%c (--%s) page offset of transfer\n", 				long_opts[i].val, long_opts[i].name				 ); i++;
  printf("  -%c (--%s) number of transfers, default is %d.\n", 			long_opts[i].val, long_opts[i].name, COUNT_DEFAULT		 ); i++;
  printf("  -%c (--%s) filename to write the unpacked data of the transfers\n", long_opts[i].val, long_opts[i].name, UNPACKED_OUTPUT_NAME_DEFAULT); i++;
  printf("  -%c (--%s) filename to write the raw data of the transfers\n", 	long_opts[i].val, long_opts[i].name, RAW_OUTPUT_NAME_DEFAULT	 ); i++;
  printf("  -%c (--%s) be more verbose during test\n", 				long_opts[i].val, long_opts[i].name				 ); i++;
  printf("  -%c (--%s) print usage help and exit\n", 				long_opts[i].val, long_opts[i].name				 ); i++;
}

static int32_t getopt_integer(char *optarg)
{
  int rc;
  int32_t value;
  rc = sscanf(optarg, "0x%x", &value);
  if (rc <= 0)
  {
    rc = sscanf(optarg, "%ul", &value);
  }
  //printf("sscanf() = %d, value = %p,0x%x,%d\n", rc, value,value,value);
  return value;
}

int main(int argc, char* argv[])
{
  int cmd_opt;
  char *device          = DEVICE_NAME_DEFAULT;
  uint32_t address  	= 0;
  uint32_t size         = SIZE_DEFAULT;
  uint32_t offset 	= 0;
  uint32_t count        = COUNT_DEFAULT;
  char *filenameraw     = RAW_OUTPUT_NAME_DEFAULT;
  char *filenameunpack  = UNPACKED_OUTPUT_NAME_DEFAULT;

  while ((cmd_opt = getopt_long(argc, argv, "vhxc:u:f:d:a:s:o:", long_opts, NULL)) != -1)
  {
    switch (cmd_opt)
    {
      case 0:
     /* long option */
        break;
      case 'v':
        verbosity++;
        break;
      /* device node name */
      case 'd':
        device = strdup(optarg);
        break;
      /* RAM address on the AXI bus in bytes */
      case 'a':
        address = getopt_integer(optarg);
        break;
      /* RAM size in bytes */
      case 's':
        size = getopt_integer(optarg);
        break;
      case 'o':
        offset = getopt_integer(optarg) & 4095;
        break;
      /* count */
      case 'c':
        count = getopt_integer(optarg);
        break;
      /* file */
      case 'f':
        filenameraw = strdup(optarg);
        break;
      /* file */
      case 'u':
        filenameunpack = strdup(optarg);
        break;
      /* No write to file */
      case 'x':
        no_write++;
        break;
      /* print usage help and exit */
      case 'h':
      default:
  	usage(argv[0]);
        exit(0);
        break;
    }
  }

  if (count<0) 
  {
    count = UINT32_MAX;
  }

  //printf("device = %s\n address = 0x%x\n size = %d\n offset = 0x%x\n count = %u\n rawfilename = %s\n unpackfilename = %s\n", device, address, size, offset, count, filenameraw, filenameunpack);
  run_dma(device, address, size, offset, count, filenameraw, filenameunpack);
}

static void* readandwrite(void *arg)
{

  tr_arg_t *data = (tr_arg_t *)arg;

  memset(data->buffer, 0x00, data->size);

  /* select AXI MM address */
  off_t off = lseek(data->fpga_fd, data->addr, SEEK_SET);

  /* read data from AXI MM into buffer using SGDMA */
  data->rc = read(data->fpga_fd, data->buffer, data->size);
  if ((data->rc > 0) && (data->rc < data->size)) 
  {
    printf("INFO --- Short read of %d bytes into a %d bytes buffer\n", data->rc, data->size);
  }

   if (data->rc != data->size) {
      printf("PRE-fileraw_fd\n");
      printf("buffer: %x\n",data->buffer);
      printf("data->rc (%d) != data->size (%d)!!!\n",data->rc,data->size);
  }

  /* write data to file */
  if ((data->fileraw_fd >= 0) & (no_write == 0)) 
  {

    /* write raw buffer to file */
    fwrite(data->buffer, data->size, 1, data->fileraw_fd);

    /* write unpacked buffer to file */
    int buffer_words = data->size/sizeof(data->dummy);
    int ith_word = -1;

    /* unpack data on-the-fly */
    while(ith_word++ < buffer_words-1)
    {

      //if ( ((uint64_t *)data->buffer)[ith_word] == 0) continue;
      uint32_t TDC_MEAS                = -1 + (uint32_t)(((uint64_t *)data->buffer)[ith_word] >> 0  ) & 0x1F;	// from 1 to 30 -> 0 to 29
      uint32_t BX_COUNTER              =      (uint32_t)(((uint64_t *)data->buffer)[ith_word] >> 5  ) & 0xFFF;
      uint32_t ORBIT_CNT               =      (uint32_t)(((uint64_t *)data->buffer)[ith_word] >> 17 ) & 0xFFFFFFFF;
      uint32_t TDC_CHANNEL             =  1 + (uint32_t)(((uint64_t *)data->buffer)[ith_word] >> 49 ) & 0x1FF;   // channel 0 -> 1
      uint32_t FPGA                    =      (uint32_t)(((uint64_t *)data->buffer)[ith_word] >> 58 ) & 0xF  ;
      uint32_t HEAD                    =      (uint32_t)(((uint64_t *)data->buffer)[ith_word] >> 62 ) & 0x3  ;

      if (TDC_CHANNEL==137 || TDC_CHANNEL==138) 
      {
        TDC_MEAS += 1;
      }

      if(verbosity>0) 
      {
        printf("FULL WORD            = %" PRIu64 "\n", ((uint64_t *)data->buffer)[ith_word]);
        printf("TDC MEAS             = %" PRIu32 "\n", TDC_MEAS);
        printf("BX COUNTER           = %" PRIu32 "\n", BX_COUNTER);
        printf("ORBIT CNT            = %" PRIu32 "\n", ORBIT_CNT);
        printf("TDC CHANNEL          = %" PRIu32 "\n", TDC_CHANNEL);
        printf("# FPGA               = %" PRIu32 "\n", FPGA);
        printf("HEAD                 = %" PRIu32 "\n", HEAD);
      }

      char wordbuffer[100];
      size_t len = sprintf(wordbuffer,"%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32"\n",HEAD,FPGA,TDC_CHANNEL,ORBIT_CNT,BX_COUNTER,TDC_MEAS);
      fwrite(wordbuffer, 1, len, data->fileunpack_fd);
    }

  }

}


static int run_dma(char *devicename, uint32_t addr, uint32_t size, uint32_t offset, uint32_t count, char *filenameraw, char *filenameunpack)
{

  int rc;
  uint64_t *buffer = NULL;
  uint64_t *allocated = NULL;
  uint64_t dummy;

  posix_memalign((void **)&allocated, 8, size);

  assert(allocated && "ERROR! --- Pointer of memory allocated via posix_memalign is not valid\n");
  buffer = allocated + offset;

  int fpga_fd = open(devicename, O_RDWR | O_NONBLOCK);
  assert(fpga_fd >= 0 && "ERROR! --- Cannot connecto to the fpga\n");

  FILE *fileraw_fd;
  FILE *fileunpack_fd;

  uint32_t iterator = 0;

  char *newfilenameraw = (char*)malloc((strlen(filenameraw)+12) * sizeof(char));
  sprintf(newfilenameraw, "%s_%06d%s", filenameraw, iterator,".dat");

  char *newfilenameunpack = (char*)malloc((strlen(filenameunpack)+12) * sizeof(char));
  sprintf(newfilenameunpack, "%s_%06d%s", filenameunpack, iterator,".txt");

  if (newfilenameraw) {
    fileraw_fd = fopen(newfilenameraw , "w" );
  }
  if (newfilenameunpack) {
    fileunpack_fd = fopen(newfilenameunpack , "w" );
    char header[] = "HEAD,FPGA,TDC_CHANNEL,ORBIT_CNT,BX_COUNTER,TDC_MEAS\n" ;
    fwrite(header , sizeof(header)-1, 1, fileunpack_fd );
  }

  pthread_t tr[1000];
  tr_arg_t tr_arg[1000];

  while (count--) {

    if ( abs(count+1) % 10240 == 0 ) { 
      // 10MB (or count limit) reached
      // close current file and open new file with incremental numbering

      iterator++;

      if (fileraw_fd != NULL) {
        fclose(fileraw_fd);
      } 
      if (fileunpack_fd != NULL) {
        fclose(fileunpack_fd);
      }

      newfilenameraw = (char*)malloc((strlen(filenameraw)+12) * sizeof(char));
      sprintf(newfilenameraw, "%s_%06d%s", filenameraw, iterator,".dat");

      newfilenameunpack = (char*)malloc((strlen(filenameunpack)+12) * sizeof(char));
      sprintf(newfilenameunpack, "%s_%06d%s", filenameunpack, iterator,".txt");

      fileraw_fd = fopen(newfilenameraw , "w" );

      fileunpack_fd = fopen(newfilenameunpack , "w" );
      char header[] = "HEAD,FPGA,TDC_CHANNEL,ORBIT_CNT,BX_COUNTER,TDC_MEAS\n" ;
      fwrite(header , 1 , sizeof(header)-1 , fileunpack_fd );
    }

    int acount = count%1000;

    tr_arg[acount].buffer        = buffer;
    tr_arg[acount].size          = size;
    tr_arg[acount].fpga_fd	= fpga_fd;
    tr_arg[acount].addr          = addr;
    tr_arg[acount].rc            = rc;
    tr_arg[acount].dummy         = dummy;
    tr_arg[acount].fileraw_fd    = fileraw_fd;
    tr_arg[acount].fileunpack_fd = fileunpack_fd;

    pthread_create(&tr[acount],NULL,readandwrite,&tr_arg[acount]);

    pthread_join(tr[acount],NULL);
     
  }

  close(fpga_fd);

  if (fileraw_fd != NULL) {
    fclose(fileraw_fd);
  }

  if (fileunpack_fd != NULL) {
    fclose(fileunpack_fd);
  }

  return(0);

}

