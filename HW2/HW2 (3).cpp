#include <stdio.h>
#include <iostream>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <vector>
#include <sys/types.h> 
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include<sstream>

#include "json.hpp"

using namespace std;
using json = nlohmann::json;

int main(int argc , char *argv[])
{
    json user;
    while(1)
    {
        int sockfd = 0;
        sockfd = socket(AF_INET , SOCK_STREAM , 0);

        if (sockfd == -1){
            printf("Fail to create a socket.");
        }

        struct sockaddr_in info;
        bzero(&info,sizeof(info));
        info.sin_family = PF_INET;
        info.sin_addr.s_addr = inet_addr("140.113.207.51");
        info.sin_port = htons(8001);

       	char buf[100]="";
      	string client="";
        getline(cin, client);
        istringstream iss(client);
        vector<string> split((istream_iterator<string>(iss)), istream_iterator<string>());
        if(split[0] != "register" && split[0] != "login")
        {
            if(user.find(split[1]) != user.end())
            {
                split[1] = user[split[1]];
            }
            client = "";
            for(int i = 0; i < split.size(); i++)
            {
                client += (split[i] + " ");
            }
        }
     	strcpy(buf, client.c_str());
      	//printf("%s\n",buf );
        connect(sockfd,(struct sockaddr *)&info,sizeof(info));
  		send(sockfd,buf,sizeof(buf),0);


   	    char buffer[100];
        for(int i = 0; i < 100; i++)
        {
            buffer[i] = '\0';
        }
  		recv(sockfd,buffer,sizeof(buffer),0);
   		
   		//printf("%s\n",buffer);
   		close(sockfd);
   		auto JsonResponse = json::parse(buffer);
        if(JsonResponse["status"] == 0)
        {
            if(JsonResponse.find("message") != JsonResponse.end())
            {
                string a = JsonResponse["message"];
                cout << a << endl;
            }
            if(JsonResponse.find("token") != JsonResponse.end())
            {
                user[split[1]] = JsonResponse["token"];
            }
            if(JsonResponse.find("invite") != JsonResponse.end())
            {
                for(json::iterator it = JsonResponse["invite"].begin(); it != JsonResponse["invite"].end(); ++it)
                {
                    string b = *it;
                    cout << b << endl;
                }

}
            if(JsonResponse.find("friend") != JsonResponse.end())
            {
                for(json::iterator it = JsonResponse["friend"].begin(); it != JsonResponse["friend"].end(); ++it)
                {
                    string c = *it;
                    cout << c << endl;
                }
            }
            if(JsonResponse.find("post") != JsonResponse.end())
            {
                for(json::iterator it = JsonResponse["post"].begin(); it != JsonResponse["post"].end(); ++it)
                {
                    auto a = *it;
                    string d = a["id"];
                    string e = a["message"];
                    cout << d << ": " << e << endl;
                }
            }
        }
        else
        {
            string f = JsonResponse["message"];
            cout << f << endl;
        }

    }



    

	


    return 0;
}