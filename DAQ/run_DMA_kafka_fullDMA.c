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

  rd_kafka_t *rk;           /* Producer instance handle */
  rd_kafka_topic_t *rkt;    /* Topic object */
  rd_kafka_conf_t *conf;    /* Temporary configuration object */
  char errstr[64];          /* librdkafka API error reporting buffer */

  while ( (cmd_opt = getopt_long(argc, argv, "vhc:b:t:d:a:s:o:", long_opts, NULL) ) != -1) {
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
  uint64_t dummyword;
  posix_memalign((void **)&allocated, 4096/*8*/, size+4096);
  assert(allocated && "ERROR! --- Pointer of memory allocated via posix_memalign is not valid\n");
  buffer = allocated + offset;
  int fpga_fd = open(device, O_RDWR | O_NONBLOCK);
  assert(fpga_fd >= 0 && "ERROR! --- Cannot connecto to the fpga\n");

  /* Signal handler for clean shutdown */     
  signal(SIGINT, stop);

  while (run && count--) {

    memset(buffer, offset, size);
    off_t off = lseek(fpga_fd, address, SEEK_SET); /* select AXI MM address */
    rc = read(fpga_fd, buffer, size); /* read data from AXI MM into buffer using SGDMA */

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
      retry:
        // Try producing the message to the topic
        if (rd_kafka_produce(rkt,                   // Topic object
                             RD_KAFKA_PARTITION_UA, // Use builtin partitioner to select partition
                             RD_KAFKA_MSG_F_COPY,   // Make a copy of the payload.
                             buffer, // aword, //buffer,
                             size, // aword_len,//size,                   // Message payload (value) and length
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

          printf("%2d | %2d | %4d | %11"PRIu32" | %5d | %3d\n", HEAD, FPGA, TDC_CHANNEL, ORBIT_CNT, BX_COUNTER, TDC_MEAS);  
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

  return(0);

}

