/**
 * READ DATA FROM DMA 
 *
 * COMPILE INCLUDING THE LIBRARIES lpthread 
 * gcc run_test.c -lpthread -lrt -o run_test
 */

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
#include <signal.h>
#include <pthread.h> 

#define DEVICE_NAME_DEFAULT "/dev/xdma0_c2h_0"
#define ADDRESS_DEFAULT (0)
#define SIZE_DEFAULT (1024)
#define OFFSET_DEFAULT (0)
#define COUNT_DEFAULT (UINT32_MAX)
#define VERBOSITY_DEFAULT (0)
#define RW_MAX_SIZE 0x7ffff000
#define RAW_OUTPUT_NAME_DEFAULT "output_raw.dat"
#define UNPACKED_OUTPUT_NAME_DEFAULT "output_unpacked.txt"
#define EXCLUDE_WRITEOUT_DEFAULT (0)

static int run = 1;

/**
 * @brief Signal termination of program
 */
static void stop (int _) {
  (void)_;
  run = 0;
}

/**
 * @brief DAQ Options
 */
static struct option const long_opts[] = {
  {"device",          required_argument,  NULL, 'd'},
  {"address",         required_argument,  NULL, 'a'},
  {"size",            required_argument,  NULL, 's'},
  {"offset",          required_argument,  NULL, 'o'},
  {"count",           required_argument,  NULL, 'c'},
  {"verbose",         required_argument,  NULL, 'v'},
  {"file",            required_argument,  NULL, 'f'},
  {"unpacked",        required_argument,  NULL, 'u'},
  {"exclude-writeout",required_argument,  NULL, 'x'},
  {"help",            no_argument,        NULL, 'h'},
  {0,                 0,                  0,    0  }
};

static void usage(const char* name) {
  int i = 0;
  printf("%s\n\n", name);
  printf("usage: %s [OPTIONS]\n\n", name);
  printf("  -%c (--%s) device (defaults to %s)\n",                              long_opts[i].val, long_opts[i].name, DEVICE_NAME_DEFAULT         ); i++;
  printf("  -%c (--%s) address of the start address on the AXI bus\n",          long_opts[i].val, long_opts[i].name, ADDRESS_DEFAULT             ); i++;
  printf("  -%c (--%s) size of a single transfer in bytes, default is %d.\n",   long_opts[i].val, long_opts[i].name, SIZE_DEFAULT                ); i++;
  printf("  -%c (--%s) page offset of transfer\n",                              long_opts[i].val, long_opts[i].name, OFFSET_DEFAULT              ); i++;
  printf("  -%c (--%s) number of transfers, default is %d.\n",                  long_opts[i].val, long_opts[i].name, COUNT_DEFAULT               ); i++;
  printf("  -%c (--%s) be more verbose during test\n",                          long_opts[i].val, long_opts[i].name, VERBOSITY_DEFAULT           ); i++;
  printf("  -%c (--%s) name for unpacked data file\n",                          long_opts[i].val, long_opts[i].name, UNPACKED_OUTPUT_NAME_DEFAULT); i++;
  printf("  -%c (--%s) name for raw data file\n",                               long_opts[i].val, long_opts[i].name, RAW_OUTPUT_NAME_DEFAULT     ); i++;
  printf("  -%c (--%s) exclude saving files\n",                                 long_opts[i].val, long_opts[i].name, EXCLUDE_WRITEOUT_DEFAULT    ); i++;
  printf("  -%c (--%s) print usage help and exit\n",                            long_opts[i].val, long_opts[i].name                              ); i++;
}

static int32_t getopt_integer(char *optarg) {
  int rc;
  int32_t value;
  rc = sscanf(optarg, "0x%x", &value);
  if (rc <= 0) {
    rc = sscanf(optarg, "%ul", &value);
  }
  return value;
}

/**
 * @alternative method to perform DMA readouts
 */
int read_to_buffer(char *fname, 
                   int fd, 
                   char *buffer, 
                   uint64_t size, 
                   uint64_t base) {
  ssize_t rc;
  uint64_t count = 0;
  char *buf = buffer;
  off_t offset = base;

  while (count < size) {
    uint64_t bytes = size - count;

    if (bytes > RW_MAX_SIZE)
      bytes = RW_MAX_SIZE;

    if (offset) {
      rc = lseek(fd, offset, SEEK_SET);
      if (rc != offset) {
        fprintf(stderr, "%s, seek off 0x%lx != 0x%lx.\n", fname, rc, offset);
        perror("seek file");
        return -1;
      }
    }

    /* read data from file into memory buffer */
    rc = read(fd, buf, bytes);
    if (rc != bytes) {
      fprintf(stderr, "%s, R off 0x%lx, 0x%lx != 0x%lx.\n",fname, count, rc, bytes);
      perror("read file");
      return -1;
    }

    count += bytes;
    buf += bytes;
    offset += bytes;
  }        

  if (count != size) {
    fprintf(stderr, "%s, R failed 0x%lx != 0x%lx.\n", fname, count, size);
    return -1;
  }
  return count;
}

int main(int argc, char* argv[]) {
  int cmd_opt;
  char *device          = DEVICE_NAME_DEFAULT;
  uint32_t address      = ADDRESS_DEFAULT;
  uint32_t size         = SIZE_DEFAULT;
  uint32_t offset       = OFFSET_DEFAULT;
  uint32_t count        = COUNT_DEFAULT;
  int verbosity         = VERBOSITY_DEFAULT;
  char *filenameraw     = RAW_OUTPUT_NAME_DEFAULT;
  char *filenameunpack  = UNPACKED_OUTPUT_NAME_DEFAULT;
  int no_write          = EXCLUDE_WRITEOUT_DEFAULT;

  while ( (cmd_opt = getopt_long(argc, argv, "vhxc:f:u:d:a:s:o:", long_opts, NULL) ) != -1) {
    switch (cmd_opt){
      case 0: /* long option */
        break;
      case 'v': /* verbosity */
        verbosity++;
        break;
      case 'd': /* device node name */
        device = strdup(optarg);
        break;
      case 'a': /* address in bytes */
        address = getopt_integer(optarg);
        break;
      case 's': /* size in bytes */
        size = getopt_integer(optarg);
        break;
      case 'o': /* offset */
        offset = getopt_integer(optarg) & 4095;
        break;
      case 'c': /* counter of tansfers */
        count = getopt_integer(optarg);
        break;      
      case 'f': /* raw filename */
        filenameraw = strdup(optarg);
        break;
      case 'u': /* unpacked filename */
        filenameunpack = strdup(optarg);
        break;      
      case 'x': /* exclude writing to file */
        no_write++;
        break;
      case 'h': /* print usage help and exit */
      default:
    usage(argv[0]);
        exit(0);
        break;
    }
  }

  int rc = -1;
  char *buffer = NULL;
  char *allocated = NULL;
  uint64_t dummyword;
  posix_memalign((void **)&allocated, 4096/*8*/, size+4096);
  assert(allocated && "ERROR! --- Pointer of memory allocated via posix_memalign is not valid\n");
  buffer = allocated + offset;
  int fpga_fd = open(device, O_RDWR | O_NONBLOCK);
  assert(fpga_fd >= 0 && "ERROR! --- Cannot connecto to the fpga\n");

  /* Signal handler for clean shutdown */
  signal(SIGINT, stop);

  /* Create files */
  FILE *fileraw_fd;
  FILE *fileunpack_fd;
  uint32_t filenumber = 0;
  char header[] = "HEAD,FPGA,TDC_CHANNEL,ORBIT_CNT,BX_COUNTER,TDC_MEAS\n" ;
  char *newfilenameraw = (char*)malloc((strlen(filenameraw)+12) * sizeof(char));
  char *newfilenameunpack = (char*)malloc((strlen(filenameunpack)+12) * sizeof(char));

  if (!no_write) { 
    sprintf(newfilenameraw, "%s_%06d%s", filenameraw, filenumber,".dat");
    sprintf(newfilenameunpack, "%s_%06d%s", filenameunpack, filenumber,".txt");
    if (newfilenameraw)
      fileraw_fd = fopen(newfilenameraw , "w" );
    if (newfilenameunpack) {
      fileunpack_fd = fopen(newfilenameunpack , "w" );
      fwrite(header , sizeof(header)-1, 1, fileunpack_fd );
    }
  }

  while (run && count--) {

    if ( (abs(count+1) % 10240 == 0) && !no_write) { 
      // 10MB (or count limit) reached
      // close current file and open new file with incremental numbering
      filenumber++;
      if (fileraw_fd != NULL)
        fclose(fileraw_fd);
      if (fileunpack_fd != NULL)
        fclose(fileunpack_fd);
      sprintf(newfilenameraw, "%s_%06d%s", filenameraw, filenumber,".dat");
      sprintf(newfilenameunpack, "%s_%06d%s", filenameunpack, filenumber,".txt");
      fileraw_fd = fopen(newfilenameraw , "w" );
      fileunpack_fd = fopen(newfilenameunpack , "w" );
      fwrite(header , 1 , sizeof(header)-1 , fileunpack_fd );
    }

    /**
      * alternative method to perform DMA readouts - 1
      *
      **/
    memset(buffer, offset, size);
    off_t off = lseek(fpga_fd, address, SEEK_SET); /* select AXI MM address */
    rc = read(fpga_fd, buffer, size); /* read data from AXI MM into buffer using SGDMA */

    /**
      * alternative method to perform DMA readouts - 2
      *
      **/
    // rc = read_to_buffer(device, fpga_fd, buffer, size, address);

    if (rc < 0) {
        printf("WARNING --- Error while reading a buffer from DMA\n");
        continue;
    }
    else if (rc == 0) {
        printf("INFO --- Read an empty buffer from DMA, while expecting %d bytes\n", size);
    }
    else if (rc < size) {
        printf("INFO --- Short read of %d bytes into a %d bytes buffer\n", rc, size);
    }
    else if (rc > size) {
        printf("WARNING --- Read a buffer of %d bytes from DMA exceeding the expected %d bytes size\n", rc, size);
        continue;
    }


    if (rc>0) {

      if (fileraw_fd!=NULL && !no_write) 
        fwrite(buffer, rc, 1, fileraw_fd);

      int buffer_words = rc/sizeof(dummyword);
      int ith_word = -1;

      /* unpack data on-the-fly */
      while(ith_word++ < buffer_words-1) {

        uint32_t TDC_MEAS                =      (uint32_t)(((uint64_t *)buffer)[ith_word] >> 0  ) & 0x1F;
        uint32_t BX_COUNTER              =      (uint32_t)(((uint64_t *)buffer)[ith_word] >> 5  ) & 0xFFF;
        uint32_t ORBIT_CNT               =      (uint32_t)(((uint64_t *)buffer)[ith_word] >> 17 ) & 0xFFFFFFFF;
        uint32_t TDC_CHANNEL             =  1 + (uint32_t)(((uint64_t *)buffer)[ith_word] >> 49 ) & 0x1FF;   // channel 0 -> 1
        uint32_t FPGA                    =      (uint32_t)(((uint64_t *)buffer)[ith_word] >> 58 ) & 0xF  ;
        uint32_t HEAD                    =      (uint32_t)(((uint64_t *)buffer)[ith_word] >> 62 ) & 0x3  ;

        if (TDC_CHANNEL!=137 && TDC_CHANNEL!=138) {
          TDC_MEAS -= 1;
        }

        if(fileunpack_fd!=NULL && !no_write){
          char wordbuffer[100];
          size_t len = sprintf(wordbuffer,"%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32"\n",HEAD,FPGA,TDC_CHANNEL,ORBIT_CNT,BX_COUNTER,TDC_MEAS);
          fwrite(wordbuffer, 1, len, fileunpack_fd);
        }

        if(verbosity>0) {
            printf("%2d | %2d | %4d | %11"PRIu32" | %5d | %3d\n", HEAD, FPGA, TDC_CHANNEL, ORBIT_CNT, BX_COUNTER, TDC_MEAS);  
        } 
      }
    }
  }

  close(fpga_fd);

  if (fileraw_fd != NULL)
    fclose(fileraw_fd);

  if (fileunpack_fd != NULL)
    fclose(fileunpack_fd);

  return(0);

}

