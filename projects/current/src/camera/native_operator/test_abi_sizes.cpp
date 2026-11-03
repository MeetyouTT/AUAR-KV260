#include "native_bridge.h"
#include <cstddef>
#include <iostream>
int main() {
  std::cout<<"{\"abi\":2,\"Report\":"<<sizeof(AuraNativeReport)
      <<",\"Ack\":"<<sizeof(AuraNativeAck)<<",\"Recovery\":"<<sizeof(AuraRecoveryState)
      <<",\"State\":"<<sizeof(AuraNativeState)<<",\"Seed\":"<<sizeof(AuraNativeSeed)
      <<",\"result_token_offset\":"<<offsetof(AuraNativeReport,result_token)
      <<",\"recovery_offset\":"<<offsetof(AuraNativeState,recovery)<<"}\n";
}
