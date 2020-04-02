package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"

	sls "github.com/aliyun/aliyun-log-go-sdk"
)

func panicCheck(err error, msg string) {
	if err != nil {
		fmt.Println(err)
		panic(msg)
	}
}

var AccessKeyID = flag.String("access-key-id", "", "")
var AccessKeySecret = flag.String("access-key-secret", "", "")
var Endpoint = flag.String("endpoint", "", "")
var Project = flag.String("project", "", "")
var Method = flag.String("method", "", "")
var Config = flag.String("config", "", "file path")

func main() {
	sls.GlobalForceUsingHTTP = true
	flag.Parse()

	if len(*AccessKeySecret) == 0 || len(*AccessKeyID) == 0 || len(*Endpoint) == 0 ||
		len(*Project) == 0 || len(*Method) == 0 {
		panicCheck(fmt.Errorf("invalid parameters"), "ValidateParameters")
	}

	client := sls.CreateNormalInterface(*Endpoint, *AccessKeyID, *AccessKeySecret, "")
	project, err := client.GetProject(*Project)
	panicCheck(err, "GetProject")

	var configDetail []byte
	if len(*Config) > 0 {
		configDetail, err = ioutil.ReadFile(*Config)
		panicCheck(err, "ReadConfig")
	}

	switch *Method {
	case "get":
		logging, err := project.GetLogging()
		panicCheck(err, "GetLogging")
		s, _ := json.Marshal(logging)
		fmt.Print(string(s))
	case "create":
		logging := &sls.Logging{}
		panicCheck(json.Unmarshal(configDetail, logging), "ParseConfig")
		panicCheck(project.CreateLogging(logging), "CreateLogging")
	case "update":
		logging := &sls.Logging{}
		panicCheck(json.Unmarshal(configDetail, logging), "ParseConfig")
		panicCheck(project.UpdateLogging(logging), "UpdateLogging")
	}
}
