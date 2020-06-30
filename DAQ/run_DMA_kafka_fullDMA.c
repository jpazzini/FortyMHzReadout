/**
 * READ DATA FROM DMA AND PRODUCE THE ENTIRE DATA-TRANSFER TO KAFKA
 *
 * COMPILE INCLUDING THE LIBRARIES lpthread lrdkafka lz lrt
 * gcc run_test_kafka_fullDMA.c -lrdkafka -lz -lpthread -lrt -o run_test_kafka_fullDMA
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
#include <librdkafka/rdkafka.h>
#include <pthread.h> 

#define DEVICE_NAME_DEFAULT "/dev/xdma0_c2h_0"
#define ADDRESS_DEFAULT (0)
#define SIZE_DEFAULT (1024)
#define OFFSET_DEFAULT (0)
#define COUNT_DEFAULT (UINT32_MAX)
#define VERBOSITY_DEFAULT (0)
#define KAFKA_BROKER_DEFAULT "dummy_broker"
#define KAFKA_TOPIC_DEFAULT "dummy_topic"
#define RUN_NUMBER_DEFAULT (999999)


// Hit masks
const uint64_t hmaskTDC_MEAS      = 0x1F;
const uint64_t hmaskBX_COUNTER    = 0xFFF;
const uint64_t hmaskORBIT_CNT     = 0xFFFFFFFF;
const uint64_t hmaskTDC_CHANNEL   = 0x1FF;
const uint64_t hmaskFPGA          = 0xF;
const uint64_t hmaskHEAD          = 0x3;

const uint64_t hfirstTDC_MEAS     = 0;
const uint64_t hfirstBX_COUNTER   = 5;
const uint64_t hfirstORBIT_CNT    = 17;
const uint64_t hfirstTDC_CHANNEL  = 49;
const uint64_t hfirstFPGA         = 58;
const uint64_t hfirstHEAD         = 62;

// Trigger masks
const uint64_t tmaskQUAL    = 0x0000000000000001;
const uint64_t tmaskBX      = 0x0000000000001FFE;
const uint64_t tmaskTAGBX   = 0x0000000001FFE000;
const uint64_t tmaskTAGORB  = 0x01FFFFFFFE000000;
const uint64_t tmaskMCELL   = 0x0E00000000000000;
const uint64_t tmaskSL      = 0x3000000000000000;
const uint64_t tmaskHEAD    = 0xC000000000000000;

const uint64_t tfirstQUAL   = 0;
const uint64_t tfirstBX     = 1;
const uint64_t tfirstTAGBX  = 13;
const uint64_t tfirstTAGORB = 25;
const uint64_t tfirstMCELL  = 57;
const uint64_t tfirstSL     = 60;
const uint64_t tfirstHEAD   = 62;

// Runumber masks
const uint64_t rmaskRUNN    = 0xFFFFFFFF;
const uint64_t rmaskCTRL    = 0x3FFFFFFF;
const uint64_t rmaskHEAD    = 0x3;

const uint64_t rfirstRUNN   = 0;
const uint64_t rfirstCTRL   = 32;
const uint64_t rfirstHEAD   = 62;


static int run = 1;

/**
 * @brief Signal termination of program
 */
static void stop (int _) {
  (void)_;
  run = 0; 
}

/**
 * @brief Message delivery report callback.
 *
 * This callback is called exactly once per message, indicating if
 * the message was succesfully delivered
 * (rkmessage->err == RD_KAFKA_RESP_ERR_NO_ERROR) or permanently
 * failed delivery (rkmessage->err != RD_KAFKA_RESP_ERR_NO_ERROR).
 *
 * The callback is triggered from rd_kafka_poll() and executes on
 * the application's thread.
 */
static void dr_msg_cb (rd_kafka_t *rk, 
                       const rd_kafka_message_t *rkmessage, 
                       void *opaque) {
  if (rkmessage->err) {
    fprintf(stderr, "%% Message delivery failed: %s\n", rd_kafka_err2str(rkmessage->err));
  }  /* The rkmessage is destroyed automatically by librdkafka */
}

/**
 * @brief DAQ Options
 */
static struct option const long_opts[] = {
  {"device",        required_argument,  NULL, 'd'},
  {"address",       required_argument,  NULL, 'a'},
  {"size",          required_argument,  NULL, 's'},
  {"offset",        required_argument,  NULL, 'o'},
  {"count",         required_argument,  NULL, 'c'},
  {"verbose",       required_argument,  NULL, 'v'},
  {"broker",        required_argument,  NULL, 'b'},
  {"topic",         required_argument,  NULL, 't'},
  {"runnumber",     required_argument,  NULL, 'r'},
  {"help",          no_argument,        NULL, 'h'},
  {0,               0,                  0,    0  }
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
  printf("  -%c (--%s) kafka broker\n",                                         long_opts[i].val, long_opts[i].name, KAFKA_BROKER_DEFAULT        ); i++;
  printf("  -%c (--%s) kafka topic\n",                                          long_opts[i].val, long_opts[i].name, KAFKA_TOPIC_DEFAULT         ); i++;
  printf("  -%c (--%s) run number\n",                                           long_opts[i].val, long_opts[i].name, RUN_NUMBER_DEFAULT          ); i++;
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

int main(int argc, char* argv[]) {

  int cmd_opt;
  char *device          = DEVICE_NAME_DEFAULT;
  uint32_t address      = ADDRESS_DEFAULT;
  uint32_t size         = SIZE_DEFAULT;
  uint32_t offset       = OFFSET_DEFAULT;
  uint32_t count        = COUNT_DEFAULT;
  int verbosity         = VERBOSITY_DEFAULT;
  char *brokers         = KAFKA_BROKER_DEFAULT; 
  char *topic           = KAFKA_TOPIC_DEFAULT;  
  uint32_t runnumber    = RUN_NUMBER_DEFAULT;

  //----- TESTING --> WRITEOUT DATA TO FILE TO XCHECK WITH MATTEO
  // FILE *fileraw_fd;
  // fileraw_fd = fopen("testing_kafka_dump.dat" , "w" );

  rd_kafka_t *rk;           /* Producer instance handle */
  rd_kafka_topic_t *rkt;    /* Topic object */
  rd_kafka_conf_t *conf;    /* Temporary configuration object */
  char errstr[64];          /* librdkafka API error reporting buffer */

  while ( (cmd_opt = getopt_long(argc, argv, "vhc:b:t:r:d:a:s:o:", long_opts, NULL) ) != -1) {
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
      case 'b': /* broker */
        brokers = strdup(optarg);
        break;
      case 't': /* topic */
        topic = strdup(optarg);
        break;
      case 'r': /* runnumber */
        runnumber = getopt_integer(optarg);
        break;
      case 'h': /* print usage help and exit */
      default:
    usage(argv[0]);
        exit(0);
        break;
    }
  }

  /*
   * Create Kafka client configuration place-holder
   */
  conf = rd_kafka_conf_new();

  /* Set bootstrap broker(s) as a comma-separated list of
   * host or host:port (default port 9092).
   * librdkafka will use the bootstrap brokers to acquire the full
   * set of brokers from the cluster. */  
  if (rd_kafka_conf_set(conf, 
                        "bootstrap.servers", 
                        brokers,
                        errstr, 
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  }
  /* set acks = 1 */
  if (rd_kafka_conf_set(conf, 
                        "acks", 
                        "1",
                        errstr, 
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  } 
  /* set compression.type=snappy */
  if (rd_kafka_conf_set(conf, 
                        "compression.codec", 
                        "snappy",
                        errstr, 
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  }
  if (rd_kafka_conf_set(conf,
                        "queue.buffering.max.ms",
                        "0", //100
                        errstr,
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  }
  if (rd_kafka_conf_set(conf, 
                        "queue.buffering.max.messages", 
                        "500000", 
                        errstr, 
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) { 
      fprintf(stderr, "%s\n", errstr); 
      return 1;  
  }

/**** COMMENTED OUT OPTIONS
  if (rd_kafka_conf_set(conf,
                        "queue.buffering.max.kbytes",
                        "1048576",
                        errstr,
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  }
  if (rd_kafka_conf_set(conf,
                        "batch.num.messages",
                        "50000",
                        errstr,
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  }
  if (rd_kafka_conf_set(conf,
                        "message.send.max.retries",
                        "3",
                        errstr,
                        sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
  }
****/

  /* Set the delivery report callback.
   * This callback will be called once per message to inform
   * the application if delivery succeeded or failed.
   * See dr_msg_cb() above. */
  rd_kafka_conf_set_dr_msg_cb(conf, dr_msg_cb);


  /*
   * Create producer instance.
   *
   * NOTE: rd_kafka_new() takes ownership of the conf object
   *       and the application must not reference it again after
   *       this call.
   */
  rk = rd_kafka_new(RD_KAFKA_PRODUCER, conf, errstr, sizeof(errstr));
  if (!rk) { fprintf(stderr,"%% Failed to create new producer: %s\n", errstr);
      return 1;
  }

  /* Create topic object that will be reused for each message
   * produced.
   *
   * Both the producer instance (rd_kafka_t) and topic objects (topic_t)
   * are long-lived objects that should be reused as much as possible.
   */
  rkt = rd_kafka_topic_new(rk, topic, NULL);
  if (!rkt) {
      fprintf(stderr, "%% Failed to create topic object: %s\n", rd_kafka_err2str(rd_kafka_last_error()));
      rd_kafka_destroy(rk);
      return 1;
  }


  int rc = -1;
  char *buffer = NULL;
  char *allocated = NULL;
  uint64_t runnumberword = runnumber;
  posix_memalign((void **)&allocated, 4096/*8*/, size+4096);
  assert(allocated && "ERROR! --- Pointer of memory allocated via posix_memalign is not valid\n");
  buffer = allocated + offset;
  memset(buffer,0,size+sizeof(runnumberword)); // Allocate an empty buffer of size + 8B (for the runnumber word)
  memcpy(buffer,&runnumberword,sizeof(runnumberword)); // Copy the runnumber into the first 8B of the buffer
  int fpga_fd = open(device, O_RDWR | O_NONBLOCK);
  assert(fpga_fd >= 0 && "ERROR! --- Cannot connect to the fpga\n");


  /* Signal handler for clean shutdown */     
  signal(SIGINT, stop);

  while (run && count--) {

    //    memset(buffer+sizeof(runnumberword), offset, size);

    /* select AXI MM address */
    off_t off = lseek(fpga_fd, address, SEEK_SET); 
    
    /* read data from AXI MM into buffer using SGDMA */
    rc = read(fpga_fd, buffer+sizeof(runnumberword), size); // Start filling the buffer from 8B onwards

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

    //----- TESTING --> WRITEOUT DATA TO FILE TO XCHECK WITH MATTEO
    // fwrite(buffer, size+sizeof(runnumberword), 1, fileraw_fd);

    if (rc>0) {
      retry:
        // Try producing the message to the topic
        if (rd_kafka_produce(rkt,                   // Topic object
                             RD_KAFKA_PARTITION_UA, // Use builtin partitioner to select partition
                             RD_KAFKA_MSG_F_COPY,   // Make a copy of the payload.
                             buffer, 		    // Message payload (value)
                             size+sizeof(runnumberword),	// Message length
                             NULL,
                             0,                     // Optional key and its length
                             NULL                   // Message opaque, provided in
                                                    // delivery report callback as
                                                    // msg_opaque.
                            ) == -1) {
          // Failed to *enqueue* message for producing.
          fprintf(stderr, "%% Failed to produce to topic %s: %s\n", rd_kafka_topic_name(rkt), rd_kafka_err2str(rd_kafka_last_error()));

          // Poll to handle delivery reports
          if (rd_kafka_last_error() ==  RD_KAFKA_RESP_ERR__QUEUE_FULL) {
            /* If the internal queue is full, wait for messages to be delivered and then retry.
             * The internal queue represents both messages to be sent and messages that have
             * been sent or failed, awaiting their delivery report callback to be called.
             *
             * The internal queue is limited by the configuration property
             * queue.buffering.max.messages */
             rd_kafka_poll(rk, 100/*block for max 100ms*/);
             goto retry;
          }
        }

      /* A producer application should continually serve the delivery report queue by calling rd_kafka_poll()
       * at frequent intervals. Either put the poll call in your main loop, or in a dedicated thread, or call it after every
       * rd_kafka_produce() call. Just make sure that rd_kafka_poll() is still called
       * during periods where you are not producing any messages to make sure previously produced messages have their
       * delivery report callback served (and any other callbacks you register). */
      rd_kafka_poll(rk, 0/*non-blocking*/);


      if(verbosity>0) {

        int buffer_words = rc/sizeof(runnumberword);
        int ith_word = -1;

        /* unpack data on-the-fly */
        while(ith_word++ < buffer_words) {
        
          uint64_t tempHitCode = ((uint64_t *)buffer)[ith_word];
          uint32_t headHitCode = (uint32_t)(tempHitCode >> hfirstHEAD) & hmaskHEAD;

          // RunNumber
	  if ( headHitCode == 0 ) {

            uint32_t rRUNN                    =      (uint32_t)( tempHitCode >> rfirstRUNN        ) & rmaskRUNN;
            uint32_t rCTRL                    =      (uint32_t)( tempHitCode >> rfirstCTRL        ) & rmaskCTRL;
            uint32_t rHEAD                    =      (uint32_t)( tempHitCode >> rfirstHEAD        ) & rmaskHEAD;

            printf("%2d |            %6d |             %6d\n", rHEAD, rCTRL, rRUNN);

	  }
	  // Hits
          else if ( headHitCode <= 2 ) {

            uint32_t TDC_MEAS                =      (uint32_t)( tempHitCode >> hfirstTDC_MEAS    ) & hmaskTDC_MEAS;
            uint32_t BX_COUNTER              =      (uint32_t)( tempHitCode >> hfirstBX_COUNTER  ) & hmaskBX_COUNTER;
            uint32_t ORBIT_CNT               =      (uint32_t)( tempHitCode >> hfirstORBIT_CNT   ) & hmaskORBIT_CNT;
            uint32_t TDC_CHANNEL             =  1 + (uint32_t)( tempHitCode >> hfirstTDC_CHANNEL ) & hmaskTDC_CHANNEL;   // channel 0 -> 1
            uint32_t FPGA                    =      (uint32_t)( tempHitCode >> hfirstFPGA        ) & hmaskFPGA;
            uint32_t HEAD                    =      (uint32_t)( tempHitCode >> hfirstHEAD        ) & hmaskHEAD;

            if (TDC_CHANNEL!=137 && TDC_CHANNEL!=138) {
              TDC_MEAS -= 1;
            }

            printf("%2d | %2d | %4d | %11"PRIu32" | %5d | %4d\n", HEAD, FPGA, TDC_CHANNEL, ORBIT_CNT, BX_COUNTER, TDC_MEAS);  
            
          }
          // Trigger
          else if ( headHitCode == 3 ) {
                  
            uint64_t storedTrigHead     = (uint64_t)( tempHitCode & tmaskHEAD )   >> tfirstHEAD;
            uint64_t storedTrigMiniCh   = (uint64_t)( tempHitCode & tmaskSL )     >> tfirstSL;
            uint64_t storedTrigMCell    = (uint64_t)( tempHitCode & tmaskMCELL )  >> tfirstMCELL;
            uint64_t storedTrigTagOrbit = (uint64_t)( tempHitCode & tmaskTAGORB ) >> tfirstTAGORB;
            uint64_t storedTrigTagBX    = (uint64_t)( tempHitCode & tmaskTAGBX )  >> tfirstTAGBX;
            uint64_t storedTrigBX       = (uint64_t)( tempHitCode & tmaskBX )     >> tfirstBX;
            uint64_t storedTrigQual     = (uint64_t)( tempHitCode & tmaskQUAL )   >> tfirstQUAL;

            // Null trigger
            //if (storedTrigBX == 4095) {
            //}

            printf("%2"PRIu64" | %2"PRIu64" | %4"PRIu64" | %11"PRIu64" | %5"PRIu64" | %4"PRIu64" | %1"PRIu64"\n", storedTrigHead, storedTrigMiniCh, storedTrigMCell, storedTrigTagOrbit, storedTrigTagBX, storedTrigBX, storedTrigQual);  
            

          }
        }
      }
    }
  }

  close(fpga_fd);

  /* Wait for final messages to be delivered or fail.
   * rd_kafka_flush() is an abstraction over rd_kafka_poll() which
   * waits for all messages to be delivered. */
  fprintf(stderr, "%% Flushing final messages..\n");
  rd_kafka_flush(rk, 10*1000 /* wait for max 10 seconds */);

  /* Destroy topic object */
  rd_kafka_topic_destroy(rkt);

  /* Destroy the producer instance */
  rd_kafka_destroy(rk);

  //----- TESTING --> WRITEOUT DATA TO FILE TO XCHECK WITH MATTEO
  // if (fileraw_fd != NULL)
  //  fclose(fileraw_fd);

  return(0);

}

